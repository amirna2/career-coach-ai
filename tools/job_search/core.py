"""Core job search functionality for Career Coach AI."""

import logging
import requests
import trafilatura
from copy import deepcopy
from trafilatura.settings import DEFAULT_CONFIG
from ddgs import DDGS
from agents import function_tool

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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

        # Extract clean text using Trafilatura (thread-safe mode - disable timeout signals)
        try:
            # Create config with disabled timeout to avoid signal issues in threading
            config = deepcopy(DEFAULT_CONFIG)
            config['DEFAULT']['EXTRACTION_TIMEOUT'] = '0'
            clean_text = trafilatura.extract(
                content,
                config=config,
                favor_recall=True,
                include_tables=True,
                include_comments=True,
                include_formatting=False,
                no_fallback=False
            )
        except Exception as e:
            logger.error(f"Trafilatura extraction failed: {e}")
            clean_text = None
        if not clean_text:
            return False, "Trafilatura failed to extract content"
        content_lower = clean_text.lower()

        # Primary filter: strong job posting indicators
        primary_indicators = [
            'equal opp', 'equal emp',
            'benefits', 'apply now', 'apply for this job'
        ]

        found_primary = [ind for ind in primary_indicators if ind in content_lower]

        if found_primary and len(content) > 500:
            return True, f"Valid job posting: {found_primary}"

        return False, f"No primary indicators found: {found_primary}"

    except Exception as e:
        # If we can't validate, assume it's valid to be safe but log the error
        logger.warning(f"Validation error for {url}: {e}")
        return True, f"Validation error (assumed valid): {str(e)}"
