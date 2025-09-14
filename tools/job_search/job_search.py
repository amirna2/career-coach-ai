#!/usr/bin/env python3
"""
ATS Job Search - Searches Greenhouse and Lever job boards for specific titles and keywords
Uses the official DuckDuckGo search library (ddgs) for reliable results
"""

import argparse
import sys
import requests
from ddgs import DDGS
from urllib.parse import urlparse

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

                        if domain in href and is_job_link(href, domain):
                            clean_url = href.split('?')[0].split('#')[0]

                            # Extract company name to avoid duplicates
                            company = extract_company_name(clean_url, domain)

                            # Check if we already have a job from this company
                            if company in company_jobs:
                                continue

                            # Validate that the job posting has actual content
                            if validate_job_posting(clean_url):
                                found_links.add(clean_url)
                                company_jobs[company] = clean_url
                                print(clean_url)

                                if len(found_links) >= args.limit:
                                    break

                except Exception as e:
                    pass

    # Don't print summary

def is_job_link(url, domain):
    """Check if URL looks like a job posting"""
    if "boards.greenhouse.io" in domain:
        return "/jobs/" in url
    elif "jobs.lever.co" in domain:
        return url.count('/') >= 4
    return False

def extract_company_name(url, domain):
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

def validate_job_posting(url):
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

if __name__ == '__main__':
    main()
