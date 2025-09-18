#!/usr/bin/env python3
"""
ATS Job Search - Searches Greenhouse and Lever job boards for specific titles and keywords
Uses the official DuckDuckGo search library (ddgs) for reliable results
"""

import argparse
import sys
from ddgs import DDGS
from .core import _is_job_link, _extract_company_name, _validate_job_posting

def main():
    parser = argparse.ArgumentParser(description="Search ATS job boards (Greenhouse, Lever)")
    parser.add_argument('--title', required=True, help='Job title to search for')
    parser.add_argument('--keywords', default='', help='Comma-separated keywords')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of results')

    args = parser.parse_args()

    # Use keywords as-is (DuckDuckGo expression)
    keywords_expr = args.keywords.strip() if args.keywords else ""

    domains = ["boards.greenhouse.io", "jobs.lever.co"]
    found_links = set()
    company_jobs = {}  # Track jobs by company to avoid duplicates

    with DDGS() as ddgs:
        for domain in domains:
            if len(found_links) >= args.limit:
                break

            # Build single search query with DuckDuckGo expression
            query = f'site:{domain} "{args.title}"'

            if keywords_expr:
                query += f' {keywords_expr}'

            queries = [query]

            for query in queries:
                if len(found_links) >= args.limit:
                    break

                try:
                    results = ddgs.text(query, max_results=10)

                    for result in results:
                        href = result.get('href', '')
                        title = result.get('title', '')

                        if domain in href and _is_job_link(href, domain):
                            clean_url = href.split('?')[0].split('#')[0]

                            # Extract company name to avoid duplicates
                            company = _extract_company_name(clean_url, domain)

                            # Check if we already have a job from this company
                            if company in company_jobs:
                                continue

                            # Validate that the job posting has actual content
                            if _validate_job_posting(clean_url)[0]:
                                found_links.add(clean_url)
                                company_jobs[company] = clean_url
                                print(clean_url)

                                if len(found_links) >= args.limit:
                                    break

                except Exception as e:
                    pass

    # Don't print summary

if __name__ == '__main__':
    main()
