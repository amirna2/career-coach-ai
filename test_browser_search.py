#!/usr/bin/env python3
"""Test script for browser-based job search functionality."""

import sys
from tools.job_search.browser import get_search_preview, build_search_urls

def test_url_generation():
    """Test URL generation for different scenarios."""
    print("🔗 Testing URL generation...")

    # Test 1: Basic job search
    print("\n1. Basic job search:")
    urls = build_search_urls("Software Engineer")
    print(f"   Generated {len(urls)} URLs")
    for url in urls[:2]:  # Show first 2
        print(f"   - {url['platform']}: {url['description']}")

    # Test 2: With boolean expression
    print("\n2. With boolean expression:")
    urls = build_search_urls("Senior Software Engineer", "remote && (python || java) && -frontend")
    print(f"   Generated {len(urls)} URLs")
    for url in urls[:2]:  # Show first 2
        print(f"   - {url['platform']}: {url['description']}")

    # Test 3: With location and remote
    print("\n3. With location and remote filters:")
    urls = build_search_urls("Product Manager", "startup", remote=True, location="San Francisco")
    print(f"   Generated {len(urls)} URLs")
    for url in urls[:2]:  # Show first 2
        print(f"   - {url['platform']}: {url['description']}")

def test_preview():
    """Test preview functionality."""
    print("\n🔍 Testing preview functionality...")

    preview = get_search_preview(
        "Data Scientist",
        "remote && (machine learning || AI) && -intern",
        remote=True,
        location="New York"
    )

    print("Preview output:")
    print(preview[:500] + "..." if len(preview) > 500 else preview)

def test_browser_search_import():
    """Test importing the new browser_search_jobs function."""
    print("\n🔧 Testing browser_search_jobs function import...")

    try:
        from tools.job_search.browser import browser_search_jobs
        print("   ✅ Successfully imported browser_search_jobs function")

        # Verify it's a function_tool
        if hasattr(browser_search_jobs, '__wrapped__'):
            print("   ✅ Function properly decorated with @function_tool")
        else:
            print("   ⚠️  Function may not be properly decorated")

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

    return True

def main():
    """Run all tests."""
    print("🚀 Testing Browser-Based Job Search")
    print("=" * 40)

    try:
        # Test URL generation
        test_url_generation()

        # Test preview
        test_preview()

        # Test import
        if test_browser_search_import():
            print("\n✅ All tests passed!")
            print("\nTo test the actual browser opening, try:")
            print("python -c \"from tools.job_search.browser import browser_search_jobs; browser_search_jobs('Software Engineer', 'remote')\"")
        else:
            print("\n❌ Some tests failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())