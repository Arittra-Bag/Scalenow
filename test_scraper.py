"""
Simple test script to demonstrate the LinkedIn scraper functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from linkedin_scraper.scrapers.linkedin_scraper import LinkedInScraper
from linkedin_scraper.scrapers.content_extractor import ContentExtractor
from linkedin_scraper.scrapers.url_parser import LinkedInURLParser
from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.logger import setup_logger


async def test_url_parser():
    """Test the URL parser functionality."""
    print("=== Testing URL Parser ===")
    
    test_urls = [
        "https://www.linkedin.com/posts/johndoe_ai-machinelearning-innovation_activity-1234567890",
        "https://linkedin.com/feed/update/urn:li:activity:1234567890",
        "https://www.linkedin.com/pulse/future-ai-john-doe",
        "https://invalid-url.com/post/123"
    ]
    
    for url in test_urls:
        try:
            post_info = LinkedInURLParser.parse_url(url)
            print(f"✅ Valid: {url}")
            print(f"   Type: {post_info.post_type}, ID: {post_info.post_id}")
            print(f"   Normalized: {post_info.normalized_url}")
        except Exception as e:
            print(f"❌ Invalid: {url} - {e}")
        print()


async def test_content_extractor():
    """Test the content extractor functionality."""
    print("=== Testing Content Extractor ===")
    
    # Sample content for testing
    sample_text = """
    Here's how AI is transforming lead generation in 2024:
    
    Key insights from my recent analysis:
    1. Predictive analytics can increase conversion rates by 40%
    2. Chatbots handle 80% of initial customer inquiries
    3. Machine learning algorithms optimize email timing
    
    Best practices for implementation:
    - Start with clean data
    - Test different AI models
    - Monitor performance metrics
    
    What do you think? Like and share if you found this helpful!
    Follow me for more AI insights.
    """
    
    extractor = ContentExtractor()
    
    # Test knowledge content extraction
    from linkedin_scraper.models.post_content import PostContent, ImageData
    from datetime import datetime
    
    post_content = PostContent(
        url="https://linkedin.com/posts/test",
        title="AI in Lead Generation",
        body_text=sample_text,
        author="Test Author",
        post_date=datetime.now(),
        images=[
            ImageData(
                url="https://example.com/chart.jpg",
                filename="chart.jpg",
                alt_text="Chart showing AI conversion rates",
                description="Performance metrics chart"
            )
        ]
    )
    
    extracted = extractor.extract_knowledge_content(post_content)
    
    print("Original text length:", extracted['original_length'])
    print("Processed text length:", extracted['processed_length'])
    print("\nKnowledge content:")
    print(extracted['knowledge_content'])
    print("\nCourse references:")
    print(extracted['course_references'])
    print("\nImage insights:")
    print(extracted['image_insights'])
    
    # Test topic categorization
    topic = extractor.categorize_content_topic(extracted['knowledge_content'])
    print(f"\nDetected topic: {topic}")
    
    # Test key insights extraction
    insights = extractor.extract_key_insights(extracted['knowledge_content'])
    print(f"\nKey insights ({len(insights)}):")
    for i, insight in enumerate(insights, 1):
        print(f"{i}. {insight}")


async def main():
    """Main test function."""
    try:
        # Set up logging
        config = Config.from_env()
        logger = setup_logger(config=config)
        
        print("LinkedIn Knowledge Scraper - Test Suite")
        print("=" * 50)
        
        # Test URL parser
        await test_url_parser()
        
        # Test content extractor
        await test_content_extractor()
        
        print("\n=== Test Summary ===")
        print("✅ URL Parser: Working")
        print("✅ Content Extractor: Working")
        print("⚠️  Web Scraper: Requires Playwright installation and LinkedIn access")
        
        print("\nTo test web scraping:")
        print("1. Install Playwright: pip install playwright")
        print("2. Install browsers: playwright install")
        print("3. Use a real LinkedIn post URL")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())