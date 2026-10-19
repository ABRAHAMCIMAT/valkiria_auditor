"""
Lambda: eda_analysis  (Step 1 del pipeline)
Realiza el Análisis Exploratorio de Datos sobre el archivo subido a S3.

Soporta dos tipos de entrada:
  - PDF  → extrae texto, calcula estadísticas del corpus documental
  - JSON/YAML → carga dataset de controles ISO 27001 (CISO Assistant format)

Input (desde Step Functions):
    {
        "bucket": "iso27001-compliance-rag-<account>",
        "key":    "raw/<uuid>_IEEG-Resultados.pdf",
        "file_name": "IEEG-Resultados.pdf"
    }

Output:
    {
        "bucket": "...",
        "key": "...",
        "file_name": "...",
        "eda_results_key": "eda_results/<uuid>_eda.json",
        "eda_summary": { ... }
    }
"""

import io
import json
import os
import re
import statistics
import uuid
from collections import Counter
from typing import Any

import boto3
import PyPDF2

s3_client = boto3.client("s3")

BUCKET_NAME     = os.environ["BUCKET_NAME"]
RESULTS_PREFIX  = os.environ.get("RESULTS_PREFIX", "eda_results/")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Remove PDF extraction artefacts and normalize whitespace."""
    # Remove non-printable / binary artefacts
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\xC0-\xFF]", " ", text)
    # Collapse multiple spaces / newlines
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Rejoin hyphenated line-breaks
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text.strip()


def _token_count(text: str) -> int:
    """Approximate token count (words × 1.3 heuristic)."""
    words = len(text.split())
    return int(words * 1.3)


def _describe_numeric(values: list[float]) -> dict:
    if not values:
        return {}
    return {
        "count": len(values),
        "mean":  round(statistics.mean(values), 2),
        "std":   round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        "min":   round(min(values), 2),
        "p25":   round(sorted(values)[len(values) // 4], 2),
        "p50":   round(statistics.median(values), 2),
        "p75":   round(sorted(values)[3 * len(values) // 4], 2),
        "max":   round(max(values), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PDF EDA
# ─────────────────────────────────────────────────────────────────────────────

def _eda_pdf(file_bytes: bytes, file_name: str) -> dict:
    """Extract text from PDF and compute corpus statistics."""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    total_pages = len(reader.pages)

    pages_text: list[str] = []
    filtered_pages = 0

    for page in reader.pages:
        raw = page.extract_text() or ""
        cleaned = _clean_text(raw)
        tokens = _token_count(cleaned)
        if tokens < 50:          # skip cover/index pages
            filtered_pages += 1
            continue
        pages_text.append(cleaned)

    token_counts = [_token_count(p) for p in pages_text]
    total_tokens = sum(token_counts)

    # Top-20 most frequent words (excluding stopwords)
    stopwords = {
        "de", "la", "el", "en", "y", "a", "los", "las", "del", "que",
        "se", "un", "una", "con", "por", "para", "es", "su", "al", "o",
        "the", "of", "and", "to", "in", "a", "is", "that", "for", "on",
    }
    all_words = " ".join(pages_text).lower().split()
    word_freq = Counter(w for w in all_words if w not in stopwords and len(w) > 3)
    top_words = dict(word_freq.most_common(20))

    # Detect ISO control references (e.g. A.5.1, A.8.23)
    control_refs = re.findall(r"\bA\.\d{1,2}\.\d{1,2}\b", " ".join(pages_text))
    control_freq = dict(Counter(control_refs).most_common(15))

    return {
        "file_type": "pdf",
        "file_name": file_name,
        "total_pages": total_pages,
        "processed_pages": len(pages_text),
        "filtered_pages": filtered_pages,
        "filter_reason": "pages with < 50 tokens (cover/index pages)",
        "total_tokens_estimated": total_tokens,
        "tokens_per_page_stats": _describe_numeric(token_counts),
        "top_20_words": top_words,
        "iso_control_references_found": control_freq,
        "null_values": 0,
        "outlier_pages": [
            i for i, t in enumerate(token_counts) if t > 800
        ],
        "outlier_threshold_tokens": 800,
    }


# ─────────────────────────────────────────────────────────────────────────────
# JSON / YAML EDA (CISO Assistant format)
# ─────────────────────────────────────────────────────────────────────────────

def _eda_json(file_bytes: bytes, file_name: str) -> dict:
    """EDA for structured JSON dataset (ISO 27001 controls from CISO Assistant)."""
    data = json.loads(file_bytes.decode("utf-8"))

    # CISO Assistant YAML/JSON has a 'requirements' list at top level
    controls: list[dict] = []
    if isinstance(data, list):
        controls = data
    elif "requirements" in data:
        controls = data["requirements"]
    elif "controls" in data:
        controls = data["controls"]
    else:
        # Flat dict — treat values as records
        controls = list(data.values()) if isinstance(data, dict) else []

    total_records = len(controls)

    # Field analysis
    all_keys: list[str] = []
    for c in controls:
        if isinstance(c, dict):
            all_keys.extend(c.keys())
    field_counts = dict(Counter(all_keys))

    # Null analysis per field
    null_counts: dict[str, int] = {}
    for field in field_counts:
        nulls = sum(
            1 for c in controls
            if isinstance(c, dict) and not c.get(field)
        )
        if nulls > 0:
            null_counts[field] = nulls

    # Domain distribution (if 'domain' or 'ref_id' field exists)
    domain_dist: dict[str, int] = {}
    for c in controls:
        if not isinstance(c, dict):
            continue
        domain = (
            c.get("domain")
            or c.get("category")
            or (c.get("ref_id", "")[:3] if c.get("ref_id") else None)
        )
        if domain:
            domain_dist[str(domain)] = domain_dist.get(str(domain), 0) + 1

    # Text length stats
    desc_lengths = [
        _token_count(str(c.get("description", "") or ""))
        for c in controls if isinstance(c, dict)
    ]

    return {
        "file_type": "json",
        "file_name": file_name,
        "total_records": total_records,
        "fields_detected": list(field_counts.keys()),
        "field_coverage": {k: total_records - v for k, v in null_counts.items()},
        "null_counts_per_field": null_counts,
        "total_null_values": sum(null_counts.values()),
        "domain_distribution": domain_dist,
        "description_token_stats": _describe_numeric(desc_lengths),
        "cardinality": {
            "domain": len(domain_dist),
            "total_fields": len(field_counts),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAMBDA HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context: Any) -> dict:
    bucket    = event["bucket"]
    key       = event["key"]
    file_name = event.get("file_name", key.split("/")[-1])

    print(f"[INFO] EDA starting for s3://{bucket}/{key}")

    # Download file from S3
    response  = s3_client.get_object(Bucket=bucket, Key=key)
    file_bytes = response["Body"].read()

    # Dispatch by file type
    ext = file_name.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        eda_result = _eda_pdf(file_bytes, file_name)
    elif ext in ("json", "yaml", "yml"):
        eda_result = _eda_json(file_bytes, file_name)
    else:
        # Treat as plain text
        text = _clean_text(file_bytes.decode("utf-8", errors="replace"))
        eda_result = {
            "file_type": "text",
            "file_name": file_name,
            "total_tokens_estimated": _token_count(text),
            "char_count": len(text),
            "line_count": text.count("\n"),
        }

    # Persist EDA results to S3
    results_key = f"{RESULTS_PREFIX}{uuid.uuid4().hex[:8]}_{file_name}_eda.json"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=results_key,
        Body=json.dumps(eda_result, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )

    print(f"[INFO] EDA results saved to s3://{BUCKET_NAME}/{results_key}")
    print(f"[INFO] EDA summary: {json.dumps(eda_result, default=str)[:500]}")

    return {
        **event,
        "eda_results_key": results_key,
        "eda_summary": {
            "file_type":    eda_result.get("file_type"),
            "file_name":    file_name,
            "total_records_or_pages": (
                eda_result.get("total_records")
                or eda_result.get("processed_pages")
            ),
            "total_tokens": (
                eda_result.get("total_tokens_estimated")
                or eda_result.get("description_token_stats", {}).get("count")
            ),
            "null_values":  eda_result.get("total_null_values", 0),
        },
    }
