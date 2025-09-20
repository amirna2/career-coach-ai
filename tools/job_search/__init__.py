"""Job search module for Career Coach AI."""

from .browser import browser_search_jobs
from .core import build_jobs_search_query

__all__ = ['browser_search_jobs', 'build_jobs_search_query']
