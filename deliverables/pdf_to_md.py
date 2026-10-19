"""Convert Avance2.16.pdf to Markdown using pdfplumber."""
import pdfplumber
from pathlib import Path

PDF_PATH = Path(__file__).parent / "Avance2.16.pdf"
MD_PATH = Path(__file__).parent / "Avance2.16.md"


def pdf_to_markdown(pdf_path: Path) -> str:
    """Extract text from PDF and return as markdown string."""
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                lines.append(f"<!-- Page {i} -->\n")
                lines.append(text)
                lines.append("\n\n---\n\n")
    return "\n".join(lines)


def main():
    if not PDF_PATH.exists():
        print(f"[ERROR] PDF not found: {PDF_PATH}")
        return

    print(f"Converting: {PDF_PATH.name} → {MD_PATH.name}")
    md_content = pdf_to_markdown(PDF_PATH)

    MD_PATH.write_text(md_content, encoding="utf-8")
    print(f"Done. Output: {MD_PATH}")
    print(f"Size: {MD_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
