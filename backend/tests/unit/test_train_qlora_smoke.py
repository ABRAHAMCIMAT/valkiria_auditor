"""
Smoke test: runs the real training script on a tiny random multimodal model, on
CPU, with no downloads beyond what the test builds. Skipped where torch is absent.
"""

import json
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("peft")
pytest.importorskip("transformers", minversion="5.0")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "finetuning" / "training"))

import train_qlora  # noqa: E402


@pytest.fixture(scope="module")
def tiny_mistral3():
    from transformers import Mistral3ForConditionalGeneration, Mistral3Config, MistralConfig, PixtralVisionConfig

    config = Mistral3Config(
        text_config=MistralConfig(
            vocab_size=64, hidden_size=16, intermediate_size=32, num_hidden_layers=1,
            num_attention_heads=2, num_key_value_heads=2, head_dim=8,
        ),
        vision_config=PixtralVisionConfig(
            hidden_size=16, intermediate_size=32, num_hidden_layers=1, num_attention_heads=2,
            head_dim=8, image_size=16, patch_size=8,
        ),
    )
    return Mistral3ForConditionalGeneration(config)


class FakeTokenizer:
    eos_token_id = 2
    pad_token_id = None

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=False):
        return [1, 3, 4, 5]

    def encode(self, text, add_special_tokens=False):
        return [6, 7, 8]


class TestTokenization:
    def example(self):
        return {"id": "x", "messages": [
            {"role": "system", "content": "s"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a"},
        ]}

    def test_loss_only_covers_the_answer(self):
        tokens = train_qlora.tokenize_example(self.example(), FakeTokenizer(), 64)
        assert tokens["input_ids"] == [1, 3, 4, 5, 6, 7, 8, 2]
        assert tokens["labels"] == [-100, -100, -100, -100, 6, 7, 8, 2]

    def test_example_that_does_not_fit_is_an_error_not_truncated(self):
        with pytest.raises(ValueError, match="does not fit"):
            train_qlora.tokenize_example(self.example(), FakeTokenizer(), 6)

    def test_collate_pads_labels_with_ignore_index(self):
        batch = train_qlora.collate([
            {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1], "labels": [-100, 2, 3]},
            {"input_ids": [1], "attention_mask": [1], "labels": [1]},
        ], pad_token_id=0)
        assert batch["labels"][1].tolist() == [1, -100, -100]
        assert batch["attention_mask"][1].tolist() == [1, 0, 0]


class TestLora:
    def test_detects_multimodal_model(self, tiny_mistral3):
        assert train_qlora.is_multimodal(tiny_mistral3.config)

    def test_targets_exclude_the_vision_tower(self, tiny_mistral3):
        targets = train_qlora.text_model_target_modules(tiny_mistral3)
        assert targets
        assert not [name for name in targets if "vision" in name]
        vision_projections = [n for n, _ in tiny_mistral3.named_modules() if "vision" in n and n.endswith("q_proj")]
        assert vision_projections, "the test model must have vision attention layers"

    def test_a_training_step_only_moves_lora_weights(self, tiny_mistral3):
        import copy

        model = train_qlora.apply_lora(copy.deepcopy(tiny_mistral3), lora_r=2, lora_alpha=4)
        trainable = [n for n, p in model.named_parameters() if p.requires_grad]
        assert trainable and all("lora_" in n for n in trainable)
        assert not [n for n in trainable if "vision" in n]

        batch = train_qlora.collate(
            [{"input_ids": [1, 3, 4, 5], "attention_mask": [1, 1, 1, 1], "labels": [-100, -100, 4, 5]}],
            pad_token_id=0,
        )
        loss = model(**batch).loss
        assert torch.isfinite(loss)
        loss.backward()
        assert any(p.grad is not None and p.grad.abs().sum() > 0 for n, p in model.named_parameters() if "lora_B" in n)
