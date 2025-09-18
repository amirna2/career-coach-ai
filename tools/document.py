"""Document loading and context retrieval functions for Career Coach AI."""

import os
from pathlib import Path
import PyPDF2
from typing import List, Dict
from agents import function_tool


def load_text_file(file_path: Path) -> str:
    """Load content from a text file."""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def load_pdf_file(file_path: Path) -> str:
    """Load content from a PDF file."""
    try:
        text = ""
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def simple_search(query: str, text: str, source: str) -> List[Dict[str, str]]:
    """Simple keyword search in text chunks."""
    query_terms = query.lower().split()
    chunks = chunk_text(text)
    results = []

    # For general document queries, return broader content for the agent to analyze
    general_terms = ['resume', 'cv', 'background', 'profile', 'about', 'tell', 'summary', 'experience']
    is_general_query = any(term in query.lower() for term in general_terms)

    for i, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()

        if is_general_query:
            # For general queries, give higher scores to chunks with key info
            score = 0
            if any(key in chunk_lower for key in ['engineer', 'software', 'experience', 'skills', 'education']):
                score = 5
            else:
                score = 1  # Include all chunks but with lower score
        else:
            # Regular keyword search
            score = sum(1 for term in query_terms if term in chunk_lower)

        if score > 0:
            results.append({
                "content": chunk.strip(),
                "source": source,
                "score": score,
                "chunk_id": i
            })

    # Sort by relevance score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:8]  # Return more matches for general queries


def _retrieve_context(query: str) -> str:
    """
    Retrieve relevant context from professional documents based on the query.

    Args:
        query: The search query or topic to find relevant information about

    Returns:
        Formatted string with relevant chunks and their sources
    """
    # Use absolute path to ensure we can find documents from any working directory
    current_dir = Path(__file__).parent.parent
    data_dir = current_dir / "data" / "me"

    # DEBUG: Log what's happening
    print(f"DEBUG: retrieve_context called with query: {query}")
    print(f"DEBUG: Looking for documents in: {data_dir}")
    print(f"DEBUG: Directory exists: {data_dir.exists()}")
    if data_dir.exists():
        files = list(data_dir.glob("*"))
        print(f"DEBUG: Found {len(files)} files: {[f.name for f in files]}")

    documents = {}

    # Load all documents
    for file_path in data_dir.glob("*"):
        if file_path.is_file():
            print(f"DEBUG: Processing file: {file_path.name}")
            try:
                if file_path.suffix.lower() == ".pdf":
                    print(f"DEBUG: Reading PDF: {file_path}")
                    content = load_pdf_file(file_path)
                elif file_path.suffix.lower() == ".txt":
                    print(f"DEBUG: Reading TXT: {file_path}")
                    content = load_text_file(file_path)
                else:
                    print(f"DEBUG: Skipping file with extension: {file_path.suffix}")
                    continue

                print(f"DEBUG: Content length for {file_path.name}: {len(content)}")
                if content.strip():
                    documents[file_path.stem] = content
                    print(f"DEBUG: Successfully loaded {file_path.name}")
                else:
                    print(f"DEBUG: No content in {file_path.name}")
            except Exception as e:
                print(f"DEBUG: Error loading {file_path.name}: {e}")

    print(f"DEBUG: Total documents loaded: {len(documents)}")
    print(f"DEBUG: Document keys: {list(documents.keys())}")

    # Search across all documents
    all_results = []
    for doc_name, content in documents.items():
        results = simple_search(query, content, doc_name)
        all_results.extend(results)

    # Sort all results by score
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Format results
    if not all_results:
        error_msg = f"No relevant information found for query: {query}"
        print(f"DEBUG: Returning error: {error_msg}")
        return error_msg

    formatted_results = []
    for result in all_results[:5]:  # Top 5 results
        source_tag = f"[{result['source']}]"
        formatted_results.append(f"{source_tag} {result['content']}")

    final_result = "\n\n".join(formatted_results)
    print(f"DEBUG: Returning {len(final_result)} characters of results")
    print(f"DEBUG: First 200 chars: {final_result[:200]}")
    return final_result


# Create the function_tool version for agent use
retrieve_context = function_tool(_retrieve_context)