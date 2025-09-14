"""Tools for the Career Coach AI."""

import os
import logging
from pathlib import Path
import PyPDF2
from typing import List, Dict
from agents import function_tool
from ddgs import DDGS
import requests

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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
    current_dir = Path(__file__).parent
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


def _search_jobs(title: str, keywords: str = "", limit: int = 10) -> str:
    """
    Search for job postings on ATS platforms (Greenhouse, Lever) using DuckDuckGo.

    This tool supports DDGS search operators:

    Args:
        title: Job title to search for (e.g. "Software Engineer", "Robotics Engineer")
        keywords: IMPORTANT Additional search terms using DDGS operators:
            - cats dogs: Results about cats OR dogs (space = OR)
            - "cats and dogs": Exact phrase search e.g (use quotes for required phrases)
            - cats -dogs: Fewer dogs in results (- excludes terms)
            - cats +dogs: More dogs in results (+ emphasizes terms)
            - cats filetype:pdf: Search for PDFs about cats
            - dogs site:example.com: Pages about dogs from example.com
            - cats -site:example.com: Pages about cats, excluding example.com
            - intitle:dogs: Page title includes "dogs"
            - inurl:cats: Page URL includes "cats"

        limit: Maximum number of job results to return

    Returns:
        Formatted string with job URLs, one per line
    """
    logger.info(f"JOB SEARCH REQUEST - Title: '{title}', Keywords: '{keywords}', Limit: {limit}")
    logger.info(f"AGENT PARSING - Raw user request should have been logged by agent")
    logger.info(f"DDGS SYNTAX CHECK - Keywords should use quotes for exact phrases like 'remote'")

    try:
        logger.debug("Importing required modules...")

        domains = ["boards.greenhouse.io", "jobs.lever.co"]
        found_links = set()
        company_jobs = {}  # Track jobs by company to avoid duplicates

        logger.info(f"Searching domains: {domains}")

        with DDGS() as ddgs:
            logger.info("Connected to DuckDuckGo")

            for domain in domains:
                if len(found_links) >= limit:
                    logger.info(f"Limit reached ({limit}), stopping search")
                    break

                # Build search query
                query = f'site:{domain} "{title}"'
                if keywords.strip():
                    query += f' {keywords.strip()}'

                logger.info(f"Searching {domain} with query: {query}")

                try:
                    results = ddgs.text(query, max_results=10)

                    # Process results
                    result_count = 0
                    for result in results:
                        result_count += 1
                        href = result.get('href', '')
                        title_text = result.get('title', '')

                        logger.debug(f"Result {result_count}: {title_text[:50]}... | URL: {href}")

                        if domain in href and _is_job_link(href, domain):
                            clean_url = href.split('?')[0].split('#')[0]
                            company = _extract_company_name(clean_url, domain)

                            logger.info(f"Valid job link for company '{company}': {clean_url}")

                            # Check if we already have a job from this company
                            if company in company_jobs:
                                logger.debug(f"Skipping duplicate company: {company}")
                                continue

                            # Validate that the job posting has actual content
                            logger.debug(f"Validating job content for: {clean_url}")
                            if _validate_job_posting(clean_url):
                                found_links.add(clean_url)
                                company_jobs[company] = clean_url
                                logger.info(f"Added valid job: {clean_url}")

                                if len(found_links) >= limit:
                                    logger.info(f"Reached limit ({limit}), breaking")
                                    break
                            else:
                                logger.warning(f"Job validation failed: {clean_url}")
                        else:
                            logger.debug(f"Invalid job link: {href}")

                    logger.info(f"Completed {domain}: found {len([url for url in found_links if domain in url])} valid jobs")

                except Exception as e:
                    logger.error(f"Search error for {domain}: {type(e).__name__}: {e}", exc_info=True)
                    continue

        logger.info(f"Search complete: Found {len(found_links)} total jobs from companies: {list(company_jobs.keys())}")

        if not found_links:
            error_msg = f"No job postings found for '{title}' with keywords '{keywords}'"
            logger.warning(error_msg)
            return error_msg

        result_lines = [f"Found {len(found_links)} job postings for '{title}':"]
        result_lines.extend(sorted(found_links))
        final_result = "\n".join(result_lines)

        logger.info(f"Returning {len(final_result)} characters of results")
        return final_result

    except Exception as e:
        error_msg = f"Error searching for jobs: {type(e).__name__}: {str(e)}"
        logger.error(f"Critical error in job search: {error_msg}", exc_info=True)
        return error_msg


def _is_job_link(url: str, domain: str) -> bool:
    """Check if URL looks like a job posting"""
    if "boards.greenhouse.io" in domain:
        return "/jobs/" in url
    elif "jobs.lever.co" in domain:
        return url.count('/') >= 4
    return False


def _extract_company_name(url: str, domain: str) -> str:
    """Extract company name from job URL"""
    try:
        if "boards.greenhouse.io" in domain:
            # Format: https://boards.greenhouse.io/company/jobs/123456
            parts = url.split('/')
            return parts[3] if len(parts) > 3 else "unknown"
        elif "jobs.lever.co" in domain:
            # Format: https://jobs.lever.co/company/job-id
            parts = url.split('/')
            return parts[3] if len(parts) > 3 else "unknown"
    except:
        return "unknown"
    return "unknown"


def _validate_job_posting(url: str) -> bool:
    """Check if job posting has actual content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            content = response.text.lower()

            # Check for job listing page indicators - reject these
            listing_indicators = [
                'career opportunities', 'current job openings', 'all open positions', 'current openings',
                'browse all jobs', 'view all jobs', 'job listings', 'open roles', 'open positions'
            ]

            if any(indicator in content for indicator in listing_indicators):
                return False

            # Check for common job posting indicators
            job_indicators = [
                'job description', 'responsibilities', 'requirements',
                'qualifications', 'apply', 'salary', 'benefits',
                'role', 'position', 'duties', 'skills'
            ]

            # Must have at least 2 job indicators and be substantial content
            indicator_count = sum(1 for indicator in job_indicators if indicator in content)
            has_content = len(content) > 1000  # Substantial content

            return indicator_count >= 2 and has_content

        return False
    except:
        # If we can't validate, assume it's valid to be safe
        return True


# Create function_tool for job search
search_jobs = function_tool(_search_jobs)


if __name__ == "__main__":
    # Test the retrieve_context function
    print("Testing retrieve_context tool...")

    test_queries = [
        "robotics experience",
        "Python programming",
        "leadership",
        "education background"
    ]

    for query in test_queries:
        print(f"\n=== Query: {query} ===")
        result = _retrieve_context(query)  # Test the raw function
        print(result[:500] + "..." if len(result) > 500 else result)
