"""
QLoRA training entry point for SageMaker. Also runs on CPU with --no-quantize
for smoke tests.

Differences between the two base models this handles:
- Ministral 3 is multimodal and ships compressed FP8 weights, so 4-bit
  quantization needs a dequantized copy first, and LoRA targets only its text
  model: the vision tower also has q/k/v/o_proj layers it must not touch.
- Its tokenizer refuses a chat ending in an assistant turn, so the prompt comes
  from the chat template and the answer is tokenized separately.
"""

import argparse
import inspect
import json
import os

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoConfig,
    AutoModelForCausalLM,
    AutoModelForImageTextToText,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

IGNORE_INDEX = -100
DEQUANTIZED_DIR = "/tmp/base_model_bf16"
LORA_TARGET_LAYERS = r"(q_proj|k_proj|v_proj|o_proj)"
VISION_MARKERS = ("vision", "multi_modal", "mm_projector")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id", required=True)
    parser.add_argument("--epochs", type=float, default=3)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--max_seq_length", type=int, default=2048)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--gradient_accumulation", type=int, default=8)
    parser.add_argument("--max_steps", type=int, default=-1)
    parser.add_argument("--no-quantize", dest="quantize", action="store_false")
    parser.add_argument("--train_dir", default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--output_dir", default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    return parser.parse_args()


def is_multimodal(config) -> bool:
    return getattr(config, "vision_config", None) is not None


def model_class(config):
    return AutoModelForImageTextToText if is_multimodal(config) else AutoModelForCausalLM


def has_compressed_weights(config) -> bool:
    quantization = getattr(config, "quantization_config", None)
    if quantization is None:
        return False
    method = quantization.get("quant_method") if isinstance(quantization, dict) else getattr(quantization, "quant_method", "")
    return "fp8" in str(method).lower()


def dequantize_weights(model_id: str, config) -> str:
    """Save an uncompressed copy: a checkpoint cannot be both FP8 and 4-bit at load time."""
    from transformers import FineGrainedFP8Config

    print(f"[INFO] Dequantizing FP8 weights of {model_id}")
    model = model_class(config).from_pretrained(
        model_id,
        quantization_config=FineGrainedFP8Config(dequantize=True),
        torch_dtype=torch.bfloat16,
        device_map="cpu",
    )
    model.save_pretrained(DEQUANTIZED_DIR)
    del model
    return DEQUANTIZED_DIR


def load_base_model(model_id: str, quantize: bool):
    config = AutoConfig.from_pretrained(model_id)
    if not quantize:
        return model_class(config).from_pretrained(model_id)

    source = dequantize_weights(model_id, config) if has_compressed_weights(config) else model_id
    model = model_class(config).from_pretrained(
        source,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map="auto",
    )
    return prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)


def text_model_target_modules(model) -> list[str]:
    """Name the exact attention layers to adapt, leaving out the vision tower."""
    pattern = LORA_TARGET_LAYERS.strip("()").split("|")
    return [
        name
        for name, _ in model.named_modules()
        if name.rsplit(".", 1)[-1] in pattern and not any(marker in name for marker in VISION_MARKERS)
    ]


def apply_lora(model, lora_r: int, lora_alpha: int):
    config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=text_model_target_modules(model),
        bias="none",
        task_type="CAUSAL_LM",
    )
    return get_peft_model(model, config)


def as_token_ids(encoded) -> list[int]:
    """Chat templates return a plain list or an encoding, depending on the tokenizer."""
    if isinstance(encoded, dict) or hasattr(encoded, "input_ids"):
        encoded = encoded["input_ids"]
    if hasattr(encoded, "tolist"):
        encoded = encoded.tolist()
    if encoded and isinstance(encoded[0], list):
        encoded = encoded[0]
    return list(encoded)


def tokenize_example(example: dict, tokenizer, max_seq_length: int) -> dict:
    """Tokenize one chat, computing the loss only on the assistant's answer."""
    messages = example["messages"]
    if messages[-1]["role"] != "assistant":
        raise ValueError(f"Example {example.get('id')} does not end in an assistant turn")

    kwargs = {}
    if "add_generation_prompt" in inspect.signature(tokenizer.apply_chat_template).parameters:
        kwargs["add_generation_prompt"] = True
    prompt_ids = as_token_ids(tokenizer.apply_chat_template(messages[:-1], tokenize=True, **kwargs))
    answer_ids = as_token_ids(tokenizer.encode(messages[-1]["content"], add_special_tokens=False))
    answer_ids.append(tokenizer.eos_token_id)

    # An answer cut in half would teach the model to stop mid JSON
    room = max_seq_length - len(prompt_ids)
    if room < len(answer_ids):
        raise ValueError(
            f"Example {example.get('id')} does not fit in {max_seq_length} tokens "
            f"(prompt {len(prompt_ids)}, answer {len(answer_ids)})"
        )

    input_ids = prompt_ids + answer_ids
    return {
        "input_ids": input_ids,
        "attention_mask": [1] * len(input_ids),
        "labels": [IGNORE_INDEX] * len(prompt_ids) + answer_ids,
    }


def collate(features: list[dict], pad_token_id: int) -> dict:
    longest = max(len(f["input_ids"]) for f in features)

    def pad(values, fill):
        return values + [fill] * (longest - len(values))

    return {
        "input_ids": torch.tensor([pad(f["input_ids"], pad_token_id) for f in features]),
        "attention_mask": torch.tensor([pad(f["attention_mask"], 0) for f in features]),
        "labels": torch.tensor([pad(f["labels"], IGNORE_INDEX) for f in features]),
    }


def main():
    args = parse_args()
    print(f"[INFO] Training {args.model_id} from {args.train_dir}")

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

    dataset = load_dataset("json", data_files={
        "train": os.path.join(args.train_dir, "train.jsonl"),
        "validation": os.path.join(args.train_dir, "val.jsonl"),
    })
    dataset = dataset.map(
        lambda example: tokenize_example(example, tokenizer, args.max_seq_length),
        remove_columns=dataset["train"].column_names,
    )

    model = apply_lora(load_base_model(args.model_id, args.quantize), args.lora_r, args.lora_alpha)
    model.print_trainable_parameters()

    use_gpu = torch.cuda.is_available()
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.output_dir,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            per_device_train_batch_size=args.batch_size,
            per_device_eval_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation,
            learning_rate=args.learning_rate,
            bf16=use_gpu,
            lr_scheduler_type="cosine",
            warmup_steps=10,
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            save_total_limit=1,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            remove_unused_columns=False,
            report_to="none",
        ),
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        data_collator=lambda features: collate(features, pad_token_id),
    )

    trainer.train()
    metrics = trainer.evaluate()

    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    with open(os.path.join(args.output_dir, "training_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"[INFO] Adapter saved to {args.output_dir}: {metrics}")


if __name__ == "__main__":
    main()
