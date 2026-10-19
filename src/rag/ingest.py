"""
This script takes the knowledge-base in form of .PDFs, and docs and transforms
them into embeddings within a ChromaDB database.

Folders indexed:
  - knowledge-base/audit-examples/
  - knowledge-base/audit-methodology/
  - knowledge-base/iso27001/

Excluded (read directly by the agent at runtime):
  - knowledge-base/sponsor-documents/

Usage:
    python src/rag/ingest.py           # build or rebuild the full index
    python src/rag/ingest.py --reset   # delete existing index, then rebuild
"""

import argparse
import json
from pathlib import Path
import chromadb
import pdfplumber
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from docx import Document

# Global variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KB_PATH      = PROJECT_ROOT / "knowledge-base"
CHROMA_PATH  = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "iso27001_reference"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 80
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

REFERENCE_FOLDERS = {
    "audit_examples":    KB_PATH / "audit-examples",
    "audit_methodology": KB_PATH / "audit-methodology",
    "iso27001_standard": KB_PATH / "iso27001",
}

def extract_pdf(path: Path) -> str:
    """
    Extracts plain text from a PDF file, reading it page by page.

    # Params
    path : Path — absolute or relative path to the .pdf file.

    # Output
    str — concatenated text of all pages, stripped of leading/trailing whitespace.
          Returns an empty string if no text could be extracted.
    """
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text.strip()


def extract_docx(path: Path) -> str:
    """
    Extracts plain text from a Word document (.docx), joining non-empty paragraphs.

    # Params
    path : Path — absolute or relative path to the .docx file.

    # Output
    str — paragraph text joined by newlines, with blank paragraphs omitted.
    """
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(path: Path) -> str:
    """
    Dispatches text extraction to the correct handler based on file extension.

    # Params
    path : Path — path to a .pdf or .docx file.

    # Output
    str — extracted plain text, or an empty string for unsupported extensions.
    """
    if path.suffix.lower() == ".pdf":
        return extract_pdf(path)
    if path.suffix.lower() == ".docx":
        return extract_docx(path)
    return ""


def chunk_text(text: str) -> list[str]:
    """
    Splits a string into overlapping fixed-size chunks for embedding.

    # Params
    text : str — plain text to be chunked (typically the full content of one document).

    # Output
    list[str] — list of text fragments of length CHUNK_SIZE with CHUNK_OVERLAP
                characters of overlap between consecutive chunks.
    """
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def ingest_folder(collection, folder_path: Path, source_label: str) -> int:
    """
    Extracts, chunks, and upserts all PDF/DOCX files in a folder into a ChromaDB collection.

    # Params
    collection   : chromadb.Collection — target collection to upsert documents into.
    folder_path  : Path — directory containing the PDF/DOCX files to process.
    source_label : str  — label used as a prefix in chunk IDs and stored in metadata
                          (e.g. 'audit_examples', 'audit_methodology').

    # Output
    int — total number of chunks upserted from this folder.
    """
    # Collect only supported file types; ignore anything else in the folder
    files = [
        f for f in folder_path.iterdir()
        if f.suffix.lower() in (".pdf", ".docx")
    ]
    if not files:
        print(f"[!] No PDF/DOCX files found in {folder_path.name}")
        return

    total_chunks = 0
    for file_path in files:
        # Extract raw text using the appropriate handler (PDF or DOCX)
        text = extract_text(file_path)
        if not text:
            print(f"  [!] No text extracted — skipping: {file_path.name}")
            continue

        # Split the document text into overlapping fixed-size fragments
        chunks = chunk_text(text)

        # Build a stable, unique ID for each chunk so upsert is idempotent:
        # re-running the script on the same file updates rather than duplicates
        #
        # Example — file: planeacion-de-auditoria-prep-v1.1-2015.pdf, label: audit_methodology
        #   ids[0] → "audit_methodology__planeacion-de-auditoria-prep-v1.1-2015__chunk0"
        #   ids[1] → "audit_methodology__planeacion-de-auditoria-prep-v1.1-2015__chunk1"
        ids = [f"{source_label}__{file_path.stem}__chunk{i}" for i in range(len(chunks))]

        # Attach source metadata so the agent knows which document a result came from
        #
        # Example — same file:
        #   metadata[0] → {"source": "planeacion-de-auditoria-prep-v1.1-2015.pdf", "folder": "audit_methodology", "chunk": 0}
        #   metadata[1] → {"source": "planeacion-de-auditoria-prep-v1.1-2015.pdf", "folder": "audit_methodology", "chunk": 1}
        metadata = [
            {"source": file_path.name, "folder": source_label, "chunk": i}
            for i in range(len(chunks))
        ]

        # Write chunks + embeddings + metadata to ChromaDB
        collection.upsert(documents=chunks, ids=ids, metadatas=metadata)
        total_chunks += len(chunks)
        print(f"{file_path.name} → {len(chunks)} chunks")

    return total_chunks


def build_index(reset: bool = False) -> None:
    """
    Orchestrates the full ingestion pipeline: initializes ChromaDB, iterates over
    all configured reference folders, and upserts their chunked embeddings.

    # Params
    reset : bool — if True, deletes the existing collection before rebuilding,
                   ensuring a clean index. Defaults to False (incremental upsert).

    # Output
    None — prints progress to stdout and persists the index to CHROMA_PATH on disk.
    """
    print(f"\nProject root : {PROJECT_ROOT}")
    print(f"ChromaDB path: {CHROMA_PATH}")
    print(f"Embedding model: {EMBEDDING_MODEL}\n")

    # Open (or create) the persistent ChromaDB store on disk
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Load the multilingual embedding model that will convert text chunks into vectors
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    # Optional full rebuild: wipe the existing collection so no stale chunks remain
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Existing collection '{COLLECTION_NAME}' deleted.\n")
        except Exception:
            pass

    # Get the collection if it exists, otherwise create it.
    # cosine similarity is standard for sentence-level semantic search.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Process each reference folder and accumulate the total chunk count
    grand_total = 0
    for label, folder in REFERENCE_FOLDERS.items():
        if not folder.exists():
            print(f"[SKIP] Folder not found: {folder}")
            continue
        print(f"[{label}] Processing {folder.name}/")
        grand_total += ingest_folder(collection, folder, label)

    print(f"\nIngestion complete — {grand_total} chunks indexed.")
    print(f"Collection '{COLLECTION_NAME}' now holds {collection.count()} documents.")

def search_collection(query: str, n_results: int = 4, folder_filter: str = None) -> list[dict]:
    """
    Queries the ChromaDB collection with a natural language string and returns
    the most semantically similar chunks ranked by cosine similarity.

    # Params
    query         : str  — natural language question or topic to search for.
    n_results     : int  — number of results to return (default 4).
    folder_filter : str  — optional filter to restrict results to a specific folder.
                           Options: 'audit_examples', 'audit_methodology', 'iso27001_standard'.

    # Output
    list[dict] — ranked list of results, each containing:
                 'rank', 'score' (0–1, higher = more similar),
                 'source' (filename), 'folder', 'chunk' (index), 'text' (chunk content).
    """
    # Connect to the existing index — raises an error if ingest.py has not been run yet
    client     = chromadb.PersistentClient(path=str(CHROMA_PATH))
    ef         = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    collection = client.get_collection(COLLECTION_NAME, embedding_function=ef)

    # Optional metadata filter: restrict results to one source folder
    where = {"folder": folder_filter} if folder_filter else None

    # ChromaDB returns distances, not similarities. For cosine space: similarity = 1 - distance
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # Unpack and reshape into a readable list of dicts
    output = []
    for i in range(len(results["documents"][0])):
        output.append({
            "rank":   i + 1,
            "score":  round(1 - results["distances"][0][i], 4),
            "source": results["metadatas"][0][i]["source"],
            "folder": results["metadatas"][0][i]["folder"],
            "chunk":  results["metadatas"][0][i]["chunk"],
            "text":   results["documents"][0][i],
        })

    return output


def print_results(results: list[dict]) -> None:
    """
    Pretty-prints the output of search_collection to stdout.

    # Params
    results : list[dict] — output from search_collection.

    # Output
    None — prints formatted results to stdout.
    """
    for r in results:
        print(f"[#{r['rank']}] score={r['score']:.4f} | {r['source']} (chunk {r['chunk']})")
        print(f"     folder : {r['folder']}")
        print(f"     excerpt: {r['text'][:300].strip()}...")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the ISO 27001 RAG index.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing ChromaDB collection before rebuilding.",
    )
    args = parser.parse_args()
    build_index(reset=args.reset)
