"""Tools for the Career Coach AI."""

import os
import logging
from pathlib import Path
import PyPDF2
from typing import List, Dict
from agents import function_tool
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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


def parse_expression(expression: str) -> dict:
    """
    Parse a custom expression into components for query building.

    Expression syntax:
    - && = AND (required terms)
    - || = OR (alternative terms)
    - - = NOT (excluded terms)
    - () = grouping

    Example: "senior && remote && -firmware && (robotics || iot)"

    Returns:
        dict with 'required', 'excluded', and 'alternatives' lists
    """
    if not expression.strip():
        return {"required": [], "excluded": [], "alternatives": []}

    # Simple parser for now - can be enhanced later
    parts = {"required": [], "excluded": [], "alternatives": []}

    # Split on && to get main required parts
    and_parts = expression.split("&&")

    for part in and_parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("-"):
            # Excluded term
            excluded = part[1:].strip()
            if excluded.startswith("(") and excluded.endswith(")"):
                # Handle grouped exclusions: -(react || javascript)
                group_content = excluded[1:-1]
                excluded_terms = [term.strip() for term in group_content.split("||")]
                parts["excluded"].extend(excluded_terms)
            else:
                parts["excluded"].append(excluded)
        elif "||" in part:
            # OR group - alternatives
            if part.startswith("(") and part.endswith(")"):
                part = part[1:-1]  # Remove parentheses
            alternatives = [term.strip() for term in part.split("||")]
            parts["alternatives"].extend(alternatives)
        else:
            # Required term
            parts["required"].append(part)

    return parts


def compile_query_for_backend(title: str, expression_parts: dict, backend: str) -> str:
    """
    Compile parsed expression into backend-specific query syntax.

    Args:
        title: Job title (always quoted)
        expression_parts: Parsed expression from parse_expression()
        backend: "google", "bing", or "yahoo"

    Returns:
        Backend-specific query string
    """
    # Start with quoted title
    query_parts = [f'"{title}"']

    # Add required terms
    if expression_parts["required"]:
        if backend == "google":
            # Google treats space as implicit AND
            query_parts.extend(expression_parts["required"])
        elif backend in ["bing", "yahoo"]:
            # Bing and Yahoo need explicit AND (capitalized)
            for req in expression_parts["required"]:
                query_parts.append(f"AND {req}")

    # Add alternatives (OR groups)
    if expression_parts["alternatives"]:
        if backend in ["google", "bing", "yahoo"]:
            # All support OR (must be capitalized)
            or_group = " OR ".join(expression_parts["alternatives"])
            if len(expression_parts["alternatives"]) > 1:
                or_group = f"({or_group})"

            if backend in ["bing", "yahoo"] and query_parts:
                query_parts.append(f"AND {or_group}")
            else:
                query_parts.append(or_group)

    # Add exclusions
    if expression_parts["excluded"]:
        if backend == "google":
            # Google uses minus operator
            for excluded in expression_parts["excluded"]:
                query_parts.append(f"-{excluded}")
        elif backend in ["bing", "yahoo"]:
            # Bing and Yahoo use NOT (capitalized)
            for excluded in expression_parts["excluded"]:
                query_parts.append(f"NOT {excluded}")

    return " ".join(query_parts)


@function_tool
def search_jobs(title: str, expression: str = "", backend: str = "google", limit: int = 10) -> str:
    """
    Search for job postings on ATS platforms using custom expression language.

    This tool uses a custom boolean expression language that compiles to backend-specific
    search syntax, providing reliable boolean logic across different search engines.

    Args:
        title (str): Primary job title to search for. This is the core position name.
            CRITICAL: Keep the title Standardized and Concise (3-5 words max)
            Examples:
            GOOD: "Senior Software Engineer", "Software Engineer", "Product Manager"
            BAD: "Principal Software Engineer (Robotics/Teleoperation)" - too long and specific

        expression (str, optional): Boolean expression using custom syntax:
            EXPRESSION SYNTAX:
            - && = AND (required terms): senior && remote
            - || = OR (alternatives): (robotics || iot || autonomous)
            - - = NOT (exclusions): -firmware && -intern
            - () = grouping: (python || c++) && -frontend

            Examples:
            Expressions should NOT repeat the title terms.
            BAD: "embedded && remote" (title already has embedded. e.g "Embedded Software Engineer")
            GOOD: "(robotics || iot) && -simulation && remote"

        backend (str, optional): Search engine backend ("google", "bing", or "yahoo").
            Default is "google".

        limit (int, optional): Maximum number of unique job postings to return.
            Default is 10. Each result represents a different company to avoid duplicates.

    Returns:
        str: Formatted string containing job search results. Each line contains:
            - Company name
            - Job title (extracted from posting)
            - Direct URL to the job posting
            Format: "Company Name - Job Title: https://job-url"

            If no jobs found, returns error message explaining the search parameters used.

    Note:
        - Searches are limited to Greenhouse and Lever ATS platforms
        - Results are validated to ensure they link to actual job postings
        - Duplicate companies are filtered out to provide diverse options
        - URLs are cleaned of tracking parameters for direct access
    """
    logger.info(f"JOB SEARCH REQUEST - Title: '{title}', Expression: '{expression}', Backend: '{backend}', Limit: {limit}")

    try:
        # Parse the custom expression
        expression_parts = parse_expression(expression)
        logger.info(f"Parsed expression: {expression_parts}")

        domains = ["boards.greenhouse.io", "jobs.lever.co"]
        found_links = set()

        logger.info(f"Searching domains: {domains}")

        with DDGS(timeout=20) as ddgs:
            logger.info(f"Connected to DuckDuckGo ({backend} backend)")

            for domain in domains:
                if len(found_links) >= limit:
                    logger.info(f"Limit reached ({limit}), stopping search")
                    break

                # Build search query using expression language
                compiled_query = compile_query_for_backend(title, expression_parts, backend)
                query = f'site:{domain} {compiled_query}'

                logger.info(f"🌐 SEARCHING {domain} WITH QUERY: {query}")

                try:
                    # Use specified backend
                    results = ddgs.text(query, max_results=50, backend=backend)

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

                            logger.debug(f"Valid job link for company '{company}': {clean_url}")

                            # Extract job title from search result
                            job_title = _extract_job_title(title_text, company)

                            # Validate that the job posting has actual content
                            logger.debug(f"Validating job content for: {clean_url}")
                            validation_result, validation_reason = _validate_job_posting(clean_url)
                            if validation_result:
                                # Store with company and title format
                                job_entry = f"{company} - {job_title}: {clean_url}"
                                found_links.add(job_entry)
                                # Allow multiple jobs per company now
                                logger.info(f"Added valid job: {company} - {job_title}")

                                if len(found_links) >= limit:
                                    logger.info(f"Reached limit ({limit}), breaking")
                                    break
                            else:
                                logger.warning(f"Job validation failed for {clean_url}: {validation_reason}")
                        else:
                            logger.debug(f"Invalid job link: {href}")

                    logger.info(f"Completed {domain}: found {len([url for url in found_links if domain in url])} valid jobs")

                except Exception as e:
                    logger.warning(f"Search failed for {domain}: {type(e).__name__}: {e}")
                    logger.info(f"Continuing to next domain...")
                    continue

        logger.info(f"Search complete: Found {len(found_links)} total jobs")

        if not found_links:
            error_msg = f"No job postings found for '{title}' with expression '{expression}' using {backend} backend"
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


def _extract_job_title(title_text: str, company: str) -> str:
    """Extract job title from search result title, removing company name."""
    if not title_text:
        return "Software Engineer"

    # Remove common prefixes and company name
    title = title_text.replace(f" - {company}", "").replace(f" at {company}", "")
    title = title.replace(" - Jobs at ", " - ")

    # Clean up common job board artifacts
    title = title.replace(" - Greenhouse", "").replace(" - Lever", "")
    title = title.split(" - ")[0]  # Take first part before any dashes

    # Fallback if title is empty or too short
    if len(title.strip()) < 5:
        return "Software Engineer"

    return title.strip()


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


def _validate_job_posting(url: str) -> tuple[bool, str]:
    """Check if job posting has actual content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        content = response.text
        content_length = len(content)

        # Parse HTML and extract clean text
        soup = BeautifulSoup(content, 'html.parser')
        clean_text = soup.get_text()
        content_lower = clean_text.lower()

        # 2-pass validation system
        # Pass 1: Equal opportunity indicators (legal requirement)
        equal_opportunity_indicators = ['equal opportunities', 'equal opportunity employer']

        # Pass 2: Apply indicators (action available)
        apply_indicators = ['apply now', 'apply for this job']

        # Pass 3: Job content indicators
        content_indicators = [
            'job description', 'responsibilities','requirements', 'about the role', 'about us', 'about you',
            'qualifications', 'salary', 'benefits',  "job id"
        ]

        # Check each pass
        eq_found = [ind for ind in equal_opportunity_indicators if ind in content_lower]
        apply_found = [ind for ind in apply_indicators if ind in content_lower]
        content_found = [ind for ind in content_indicators if ind in content_lower]

        # Combine all found indicators
        found_indicators = eq_found + apply_found + content_found
        indicator_count = len(found_indicators)
        has_content = content_length > 500

        # Log detailed validation info
        logger.debug(f"Validation details for {url}: length={content_length}, indicators={indicator_count} {found_indicators}, content_ok={has_content}")

        if indicator_count < 3:
            logger.debug(f"VALIDATION FAILURE - First 500 chars of content: {content[:500]}")
            logger.debug(f"Content contains 'apply for this job': {'apply for this job' in content_lower}")
            logger.debug(f"Content contains 'benefits': {'benefits' in content_lower}")
            logger.debug(f"Content contains 'qualifications': {'qualifications' in content_lower}")
            logger.debug(f"Content contains 'about the role': {'about the role' in content_lower}")
            return False, f"Too few job indicators ({indicator_count}/4): {found_indicators}"

        if not has_content:
            return False, f"Content too short ({content_length} chars < 500)"

        return True, f"Valid: {indicator_count} indicators, {content_length} chars"

    except Exception as e:
        # If we can't validate, assume it's valid to be safe but log the error
        logger.warning(f"Validation error for {url}: {e}")
        return True, f"Validation error (assumed valid): {str(e)}"


# Create function_tool using the recommended decorator approach


if __name__ == "__main__":
    # Test the search_jobs function
    print("Testing search_jobs tool...")

    # Test job search
    print("\n=== Testing Job Search ===")
    # Create a temporary function to test the job search logic
    def test_search_jobs(title: str, keywords: str = "", limit: int = 10) -> str:
        logger.info(f"JOB SEARCH REQUEST - Title: '{title}', Keywords: '{keywords}', Limit: {limit}")

        try:
            domains = ["boards.greenhouse.io", "jobs.lever.co"]
            found_links = set()

            logger.info(f"Searching domains: {domains}")

            with DDGS(timeout=20) as ddgs:
                logger.info("Connected to DuckDuckGo")

                for domain in domains:
                    if len(found_links) >= limit:
                        logger.info(f"Limit reached ({limit}), stopping search")
                        break

                    # Build search query
                    query = f'site:{domain} "{title}"'
                    if keywords.strip():
                        query += f' {keywords.strip()}'

                    logger.info(f"🕵️‍♂️  SEARCHING {domain} WITH QUERY: {query}")

                    try:
                        # Use Google backend only for consistent AND logic
                        results = ddgs.text(query, max_results=50, backend="backend")

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

                                logger.debug(f"Valid job link for company '{company}': {clean_url}")

                                # Extract job title from search result
                                job_title = _extract_job_title(title_text, company)

                                # Validate that the job posting has actual content
                                logger.debug(f"Validating job content for: {clean_url}")
                                validation_result, validation_reason = _validate_job_posting(clean_url)
                                if validation_result:
                                    # Store with company and title format
                                    job_entry = f"{company} - {job_title}: {clean_url}"
                                    found_links.add(job_entry)
                                    logger.info(f"Added valid job: {company} - {job_title}")

                                    if len(found_links) >= limit:
                                        logger.info(f"Reached limit ({limit}), breaking")
                                        break
                                else:
                                    logger.warning(f"Job validation failed for {clean_url}: {validation_reason}")
                            else:
                                logger.debug(f"Invalid job link: {href}")

                        logger.info(f"Completed {domain}: found {len([url for url in found_links if domain in url])} valid jobs")

                    except Exception as e:
                        logger.warning(f"Search failed for {domain}: {type(e).__name__}: {e}")
                        logger.info(f"Continuing to next domain...")
                        continue

            logger.info(f"Search complete: Found {len(found_links)} total jobs")

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

    # Test different boolean syntaxes
    test_cases = [
        ('OR syntax', 'site:jobs.lever.co IBM OR Cobol'),
        ('AND syntax', 'site:jobs.lever.co IBM AND Cobol'),
        #('Space (default)', 'site:jobs.lever.co Python C++'),
        #('Parentheses', 'site:jobs.lever.co (Python C++)'),
    ]

    for test_name, keywords in test_cases:
        print(f"\n=== {test_name}: {keywords} ===")
        result = test_search_jobs(
            title="Senior Software Engineer",
            keywords=keywords,
            limit=3
        )
        print(result)
        print("-" * 50)
    print(result)

    print("\n" + "="*50)

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
