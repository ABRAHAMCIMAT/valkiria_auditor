"""
Drafts candidate training examples from real audit reports with Bedrock.

Every draft comes out as review_status=pending_review with reviewed_by empty, and
build_dataset.py rejects it until a person checks it against the source document
and approves it. The model only reduces the typing: it does not provide labels.

Usage:
    python draft_examples.py --input ../../knowledge-base/audit-examples/report.pdf \
        --out data/drafts/report.jsonl
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import ANNEX_A_2022  # noqa: E402

DEFAULT_MODEL_ID = "us.amazon.nova-pro-v1:0"
PASSAGE_CHARS = 6000
MAX_TOKENS = 4096

PROMPT = """Extrae los hallazgos de auditoría que aparecen de forma explícita en este fragmento
de un reporte de auditoría ISO 27001. No inventes hallazgos: si el fragmento no contiene ninguno,
responde {{"findings": []}}. La evidencia debe ser una cita textual del fragmento.

FRAGMENTO:
{passage}

Responde únicamente con JSON:
{{"findings": [{{"control_id": "<A.X.Y de ISO 27001:2022>",
"evidence": "<cita textual>",
"conformity_level": "conforming|minor_nonconformity|major_nonconformity|opportunity_for_improvement",
"maturity_score": <0-5>, "finding": "<hallazgo>", "recommendation": "<recomendación>"}}]}}"""


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    if path.suffix.lower() == ".docx":
        import docx

        return "\n".join(paragraph.text for paragraph in docx.Document(path).paragraphs)
    return path.read_text(encoding="utf-8")


def split_passages(text: str, size: int = PASSAGE_CHARS) -> list[str]:
    return [text[start:start + size] for start in range(0, len(text), size)]


def parse_findings(answer: str) -> list[dict]:
    text = answer.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    return json.loads(text).get("findings", [])


def draft_from_passage(client, model_id: str, passage: str, source_document: str) -> list[dict]:
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": PROMPT.format(passage=passage)}]}],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.0},
    )
    try:
        findings = parse_findings(response["output"]["message"]["content"][0]["text"])
    except (json.JSONDecodeError, AttributeError):
        print(f"[WARN] Unparseable answer for a passage of {source_document}, skipped")
        return []

    drafts = []
    for finding in findings:
        evidence = str(finding.get("evidence", ""))
        # A quote not present in the source is not evidence of anything
        if finding.get("control_id") not in ANNEX_A_2022 or not evidence or evidence not in passage:
            continue
        digest = hashlib.sha256(f"{source_document}:{evidence}".encode("utf-8")).hexdigest()[:16]
        drafts.append({
            **finding,
            "id": f"draft-{digest}",
            "source_document": source_document,
            "review_status": "pending_review",
            "reviewed_by": "",
        })
    return drafts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    args = parser.parse_args()

    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    passages = split_passages(extract_text(args.input))
    drafts = []
    for passage in passages:
        drafts.extend(draft_from_passage(client, args.model_id, passage, args.input.name))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for draft in drafts:
            f.write(json.dumps(draft, ensure_ascii=False) + "\n")
    print(f"[INFO] {len(drafts)} drafts from {len(passages)} passages, pending human review: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
