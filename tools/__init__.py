"""Tools package for Career Coach AI - Re-exports for backward compatibility."""

# Document handling functions
from .document import load_text_file, load_pdf_file, chunk_text, simple_search, retrieve_context

# Job search functionality (browser-based only)
from .job_search import browser_search_jobs

# Keep these imports available at package level for backward compatibility
__all__ = [
    'load_text_file',
    'load_pdf_file',
    'chunk_text',
    'simple_search',
    'retrieve_context',
    'browser_search_jobs'
]
