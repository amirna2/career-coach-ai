"""Browser-based job search functionality."""

import logging
import urllib.parse
import subprocess
import sys
import webbrowser
from agents import function_tool
from .core import parse_expression, compile_query_for_backend
from config import get_config

logger = logging.getLogger(__name__)


@function_tool
def browser_search_jobs(title: str, expression: str = "", backend: str = "google", limit: int = None) -> str:
    """
    Open ATS job searches in your default browser using intelligent query building.

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

        limit (int, optional): Maximum number of ATS domains to search.
            CRITICAL: ignore this parameter, UNLESS the user specifically requests a limit.

    Returns:
        str: Confirmation message listing which ATS platforms were opened in your browser.

    Note:
        - Searches ATS platforms: Greenhouse, Lever, Ashby
        - Uses the same query compilation logic as the scraping tool
        - Opens Google site searches for each ATS domain
        - Immediate access to actual ATS job postings
    """
    logger.info(f"BROWSER ATS SEARCH - Title: '{title}', Expression: '{expression}', Backend: '{backend}'")

    try:
        # Get configuration
        config = get_config()

        # Use config default if no limit specified
        if limit is None:
            limit = config.job_search.default_limit
        logger.info(f"=================== Using result limit: {limit}")

        # Parse the custom expression
        expression_parts = parse_expression(expression)
        logger.info(f"Parsed expression: {expression_parts}")

        # Use domains from configuration
        domains = config.job_search.domains

        opened_count = 0
        opened_platforms = []

        logger.info(f"Searching domains: {domains}")

        for domain in domains:
            compiled_query = compile_query_for_backend(title, expression_parts, backend)
            # Use robust intext filters that appear on ATS job pages
            query = f'site:{domain} {compiled_query} intext:"apply" intext:"employment"'

            logger.info(f"🌐 OPENING {domain} WITH QUERY: {query}")

            # Create Google search URL
            google_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

            try:
                # Prefer stdlib for reliability
                opened = webbrowser.open_new_tab(google_url)
                if not opened:
                    # Subprocess fallback by platform
                    if sys.platform == "darwin":  # macOS
                        subprocess.Popen(["open", google_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif sys.platform.startswith("linux"):  # Linux
                        subprocess.Popen(["xdg-open", google_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif sys.platform == "win32":  # Windows
                        subprocess.Popen(["start", google_url], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        # Last-resort stdlib
                        webbrowser.open(google_url)

                opened_count += 1
                opened_platforms.append(domain)
                logger.info(f"✅ Successfully opened {domain}")

            except Exception as e:
                logger.warning(f"Failed to open {domain}: {e}")
                continue

        if opened_count > 0:
            platforms_list = ", ".join(opened_platforms)
            result = f"Opened {opened_count} ATS job search tabs in your browser:\n"
            result += f"Platforms: {platforms_list}\n\n"
            result += f"Search query: {compiled_query}\n"
            if expression:
                result += f"Expression used: {expression}"
            return result
        else:
            return "Failed to open any ATS search tabs. Please check your default browser settings."

    except Exception as e:
        error_msg = f"Error opening ATS browser searches: {str(e)}"
        logger.error(error_msg)
        return error_msg
