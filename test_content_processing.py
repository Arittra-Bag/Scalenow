"""
Test script for the content processing pipeline with Gemini AI integration.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from linkedin_scraper.services.gemini_client import GeminiClient
from linkedin_scraper.services.content_processor import ContentProcessor
from linkedin_scraper.services.categorization_service import CategorizationService
from linkedin_scraper.models.post_content import PostContent, ImageData
from linkedin_scraper.models.knowledge_item import Category
from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.logger import setup_logger


async def test_gemini_client():
    """Test the Gemini API client."""
    print("=== Testing Gemini Client ===")
    
    try:
        client = GeminiClient()
        
        # Test connection
        print("Testing API connection...")
        connection_ok = await client.test_connection()
        print(f"✅ Connection: {'Success' if connection_ok else 'Failed'}")
        
        # Test content generation
        print("\nTesting content generation...")
        test_prompt = "Explain the key benefits of AI in business in 2-3 sentences."
        response = await client.generate_content(test_prompt)
        print(f"✅ Generated content ({len(response)} chars):")
        print(f"   {response[:100]}...")
        
        # Test rate limiting status
        print("\nRate limit status:")
        status = client.get_rate_limit_status()
        print(f"   Requests this minute: {status['requests_this_minute']}/{status['requests_per_minute_limit']}")
        print(f"   Requests today: {status['requests_today']}/{status['requests_per_day_limit']}")
        print(f"   Tokens today: {status['tokens_today']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini client test failed: {e}")
        return False


async def test_content_processor():
    """Test the content processor."""
    print("\n=== Testing Content Processor ===")
    
    try:
        processor = ContentProcessor()
        
        # Sample LinkedIn post content
        sample_post = PostContent(
            url="https://linkedin.com/posts/test-ai-post",
            title="The Future of AI in Business",
            body_text="""
            Here are the key insights from my analysis of AI adoption in enterprise:
            
            🔑 Key findings:
            1. 73% of companies report improved efficiency with AI automation
            2. Machine learning models reduce customer service response time by 60%
            3. Predictive analytics increase sales forecasting accuracy by 45%
            
            Best practices for AI implementation:
            - Start with clean, structured data
            - Focus on specific use cases first
            - Invest in employee training and change management
            - Monitor performance metrics continuously
            
            I'm offering a masterclass on AI Strategy for Business Leaders next month.
            
            What's your experience with AI in your organization? Let me know in the comments!
            Follow me for more AI insights and like if you found this helpful.
            """,
            author="AI Expert",
            post_date=datetime.now(),
            images=[
                ImageData(
                    url="https://example.com/ai-chart.jpg",
                    filename="ai-chart.jpg",
                    alt_text="Chart showing AI adoption rates across industries",
                    description="Infographic with AI statistics"
                )
            ]
        )
        
        print("Processing sample post...")
        knowledge_item = await processor.process_post_content(sample_post)
        
        print(f"✅ Knowledge item created:")
        print(f"   ID: {knowledge_item.id}")
        print(f"   Topic: {knowledge_item.topic}")
        print(f"   Category: {knowledge_item.category.value}")
        print(f"   Knowledge content ({len(knowledge_item.key_knowledge_content)} chars):")
        print(f"   {knowledge_item.key_knowledge_content[:200]}...")
        print(f"   Course references: {knowledge_item.course_references}")
        print(f"   Image insights: {knowledge_item.infographic_summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Content processor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_categorization_service():
    """Test the categorization service."""
    print("\n=== Testing Categorization Service ===")
    
    try:
        categorizer = CategorizationService()
        
        # Test different types of content
        test_contents = [
            ("Machine learning algorithms are revolutionizing predictive analytics in business", "AI & Machine Learning"),
            ("Our SaaS platform achieved 40% growth in recurring revenue this quarter", "SaaS & Business"),
            ("Email marketing campaigns with personalization see 25% higher conversion rates", "Marketing & Sales"),
            ("Effective leadership requires clear communication and team empowerment", "Leadership & Management"),
            ("Cloud computing and microservices architecture enable better scalability", "Technology Trends"),
            ("This online course covers Python programming fundamentals and data science", "Course Content")
        ]
        
        print("Testing AI-based categorization...")
        for content, expected in test_contents:
            try:
                category, confidence = await categorizer.categorize_content(content, use_ai=True)
                print(f"✅ Content: {content[:50]}...")
                print(f"   Predicted: {category.value} (confidence: {confidence:.2f})")
                print(f"   Expected: {expected}")
                print()
                
                # Small delay between requests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Failed to categorize: {e}")
        
        # Test course reference extraction
        print("Testing course reference extraction...")
        course_content = """
        I just completed the Machine Learning Specialization on Coursera.
        Next, I'm planning to take the AWS Certified Solutions Architect certification.
        The Deep Learning course by Andrew Ng was particularly insightful.
        """
        
        courses = categorizer.extract_course_references(course_content)
        print(f"✅ Extracted courses: {courses}")
        
        return True
        
    except Exception as e:
        print(f"❌ Categorization service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_processing_stats():
    """Test processing statistics and health checks."""
    print("\n=== Testing Processing Stats ===")
    
    try:
        processor = ContentProcessor()
        
        print("Getting processing statistics...")
        stats = await processor.get_processing_stats()
        
        print(f"✅ Processing stats:")
        print(f"   Gemini status: {stats['gemini_status']['status']}")
        print(f"   API connection: {stats['gemini_status']['api_connection']}")
        print(f"   Rate limits: {stats['rate_limits']['requests_this_minute']}/{stats['rate_limits']['requests_per_minute_limit']} per minute")
        print(f"   Configuration:")
        print(f"     - Sanitize content: {stats['config']['sanitize_content']}")
        print(f"     - PII detection: {stats['config']['enable_pii_detection']}")
        print(f"     - Batch size: {stats['config']['batch_size']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Processing stats test failed: {e}")
        return False


async def main():
    """Main test function."""
    try:
        # Set up logging
        config = Config.from_env()
        logger = setup_logger(config=config)
        
        print("LinkedIn Knowledge Scraper - Content Processing Test Suite")
        print("=" * 60)
        
        # Run tests
        tests = [
            ("Gemini Client", test_gemini_client),
            ("Content Processor", test_content_processor),
            ("Categorization Service", test_categorization_service),
            ("Processing Stats", test_processing_stats)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:25} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All content processing tests passed!")
            print("\nThe AI-powered content processing pipeline is ready!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())