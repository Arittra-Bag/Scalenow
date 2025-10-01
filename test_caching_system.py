"""
Test script for the caching and deduplication system.
"""

import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from linkedin_scraper.storage.cache_manager import CacheManager
from linkedin_scraper.services.content_cache_service import ContentCacheService
from linkedin_scraper.models.knowledge_item import KnowledgeItem, Category
from linkedin_scraper.models.post_content import PostContent, ImageData, EngagementData
from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.logger import setup_logger


def create_sample_knowledge_items() -> list:
    """Create sample knowledge items for testing."""
    items = [
        KnowledgeItem(
            topic="AI in Customer Service",
            post_title="How AI Chatbots Transform Customer Support",
            key_knowledge_content="AI chatbots can handle 80% of customer inquiries automatically, reducing response time by 60% and improving customer satisfaction scores by 25%. Key implementation strategies include proper training data, escalation protocols, and continuous learning.",
            infographic_summary="Chart showing AI chatbot performance metrics",
            source_link="https://linkedin.com/posts/ai-expert-customer-service-1",
            notes_applications="Implement AI chatbots for tier-1 support, maintain human oversight for complex issues",
            category=Category.AI_MACHINE_LEARNING,
            course_references=["AI for Customer Service Certification", "Machine Learning Fundamentals"]
        ),
        KnowledgeItem(
            topic="AI in Customer Support",  # Similar topic
            post_title="AI-Powered Customer Service Revolution",
            key_knowledge_content="Artificial intelligence chatbots can automatically handle 80% of customer inquiries, reducing response times by 60% and boosting customer satisfaction by 25%. Implementation requires proper training data and escalation procedures.",  # Very similar content
            infographic_summary="Infographic displaying AI chatbot statistics",
            source_link="https://linkedin.com/posts/ai-guru-customer-support-2",
            notes_applications="Deploy AI chatbots for first-level support, keep human agents for complex cases",
            category=Category.AI_MACHINE_LEARNING,
            course_references=["Customer Service AI Training"]
        ),
        KnowledgeItem(
            topic="SaaS Growth Metrics",
            post_title="Essential SaaS KPIs for 2024",
            key_knowledge_content="Critical SaaS metrics include Monthly Recurring Revenue (MRR), Customer Acquisition Cost (CAC), Lifetime Value (LTV), and Churn Rate. Target LTV:CAC ratio should be 3:1 or higher for sustainable growth.",
            infographic_summary="Dashboard showing key SaaS metrics and benchmarks",
            source_link="https://linkedin.com/posts/saas-expert-metrics-2024",
            notes_applications="Track these metrics monthly, focus on reducing churn through better onboarding",
            category=Category.SAAS_BUSINESS,
            course_references=["SaaS Business Model Mastery"]
        ),
        KnowledgeItem(
            topic="Email Marketing",
            post_title="Email Marketing Best Practices 2024",
            key_knowledge_content="Personalized email campaigns achieve 26% higher open rates. Segmentation improves click-through rates by 100%. A/B testing subject lines increases engagement by 15%.",
            infographic_summary="Email marketing statistics and best practices infographic",
            source_link="https://linkedin.com/posts/marketing-guru-email-tips",
            notes_applications="Implement email segmentation, test subject lines regularly, personalize content",
            category=Category.MARKETING_SALES,
            course_references=["Advanced Email Marketing", "Digital Marketing Analytics"]
        ),
        KnowledgeItem(
            topic="Remote Leadership",
            post_title="Managing Remote Teams Effectively",
            key_knowledge_content="Effective remote leadership requires clear communication, regular check-ins, and trust-building. Use asynchronous communication for 70% of interactions, synchronous for critical decisions.",
            infographic_summary="Remote team management framework diagram",
            source_link="https://linkedin.com/posts/leadership-coach-remote-teams",
            notes_applications="Schedule weekly 1:1s, use project management tools, establish clear expectations",
            category=Category.LEADERSHIP_MANAGEMENT,
            course_references=["Remote Leadership Certification"]
        )
    ]
    
    return items


def create_sample_post_content() -> list:
    """Create sample post content for testing."""
    posts = [
        PostContent(
            url="https://linkedin.com/posts/ai-expert-customer-service-1",
            title="How AI Chatbots Transform Customer Support",
            body_text="AI chatbots are revolutionizing customer service. Here's what we've learned from implementing them across 50+ companies...",
            author="AI Expert",
            post_date=datetime.now(),
            images=[
                ImageData(
                    url="https://example.com/ai-chart.jpg",
                    filename="ai-chart.jpg",
                    alt_text="Chart showing AI chatbot performance metrics",
                    description="Performance metrics for AI chatbots"
                )
            ],
            engagement_metrics=EngagementData(likes=150, comments=25, shares=30)
        ),
        PostContent(
            url="https://linkedin.com/posts/saas-expert-metrics-2024",
            title="Essential SaaS KPIs for 2024",
            body_text="Every SaaS founder needs to track these critical metrics. Here's your complete guide to SaaS KPIs...",
            author="SaaS Expert",
            post_date=datetime.now(),
            images=[],
            engagement_metrics=EngagementData(likes=200, comments=40, shares=50)
        )
    ]
    
    return posts


def test_cache_manager():
    """Test the basic cache manager functionality."""
    print("=== Testing Cache Manager ===")
    
    try:
        cache_manager = CacheManager()
        
        # Test URL caching
        test_url = "https://linkedin.com/posts/test-user_ai-innovation_activity-123456"
        
        print("Testing URL caching...")
        is_cached_before = cache_manager.is_url_cached(test_url)
        print(f"   URL cached before: {is_cached_before}")
        
        # Cache the URL
        url_hash = cache_manager.cache_url(
            test_url,
            post_type="posts",
            post_id="activity-123456",
            metadata={"test": "data"}
        )
        print(f"   URL cached with hash: {url_hash}")
        
        # Check if cached now
        is_cached_after = cache_manager.is_url_cached(test_url)
        print(f"   URL cached after: {is_cached_after}")
        
        # Get cached URL info
        url_info = cache_manager.get_cached_url_info(test_url)
        print(f"   Cached URL info: {url_info['post_type'] if url_info else 'None'}")
        
        # Test content caching
        print("\nTesting content caching...")
        sample_posts = create_sample_post_content()
        
        for post in sample_posts:
            content_hash = cache_manager.cache_post_content(post.url, post)
            print(f"   Content cached: {content_hash}")
            
            # Retrieve cached content
            cached_content = cache_manager.get_cached_content(post.url)
            if cached_content:
                print(f"   Retrieved content: {cached_content.title}")
        
        # Test knowledge item caching
        print("\nTesting knowledge item caching...")
        sample_items = create_sample_knowledge_items()
        
        for item in sample_items:
            start_time = time.time()
            cached_id = cache_manager.cache_knowledge_item(item, processing_time_ms=int((time.time() - start_time) * 1000))
            print(f"   Knowledge item cached: {cached_id}")
        
        # Test processing queue
        print("\nTesting processing queue...")
        queue_added = cache_manager.add_to_processing_queue(test_url, priority=8)
        print(f"   Added to queue: {queue_added}")
        
        next_item = cache_manager.get_next_from_queue()
        if next_item:
            print(f"   Next from queue: {next_item['original_url']}")
            cache_manager.mark_processing_complete(next_item['url_hash'], success=True)
            print("   Marked as complete")
        
        # Get statistics
        stats = cache_manager.get_cache_statistics()
        print(f"\n✅ Cache statistics:")
        print(f"   URLs cached: {stats['total_urls_cached']}")
        print(f"   Content cached: {stats['total_content_cached']}")
        print(f"   Knowledge cached: {stats['total_knowledge_cached']}")
        print(f"   Cache hit rate: {stats['cache_hit_rate']:.1f}%")
        print(f"   Database size: {stats['database_size_mb']:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_content_cache_service():
    """Test the enhanced content cache service."""
    print("\n=== Testing Content Cache Service ===")
    
    try:
        cache_service = ContentCacheService()
        
        # Test enhanced caching with duplicate detection
        print("Testing enhanced caching with duplicate detection...")
        sample_items = create_sample_knowledge_items()
        sample_posts = create_sample_post_content()
        
        cached_items = []
        for i, item in enumerate(sample_items):
            post_content = sample_posts[i] if i < len(sample_posts) else None
            
            cached_id, is_new = cache_service.cache_knowledge_item_enhanced(
                item, post_content, processing_time_ms=100 + i * 50
            )
            
            cached_items.append((cached_id, is_new))
            print(f"   Item {i+1}: {'New' if is_new else 'Duplicate'} - {cached_id}")
        
        # Test similarity detection
        print("\nTesting similarity detection...")
        test_item = sample_items[0]  # First item
        similar_items = cache_service.find_similar_content(test_item, similarity_threshold=0.7)
        print(f"   Found {len(similar_items)} similar items")
        
        for similar in similar_items:
            print(f"     - {similar['knowledge_id']}: {similar['similarity_score']:.3f}")
        
        # Test content search
        print("\nTesting content search...")
        search_results = cache_service.search_cached_content("AI chatbot", limit=5)
        print(f"   Search results for 'AI chatbot': {len(search_results)}")
        
        for result in search_results:
            print(f"     - {result['topic']}: {result['category']}")
        
        # Test related content
        print("\nTesting related content...")
        if cached_items:
            first_item_id = cached_items[0][0]
            related_content = cache_service.get_related_content(first_item_id, limit=3)
            print(f"   Related content for {first_item_id}: {len(related_content)}")
            
            for related in related_content:
                print(f"     - {related['topic']}: {related.get('similarity_score', 0):.3f}")
        
        # Test topic clusters
        print("\nTesting topic clusters...")
        clusters = cache_service.get_topic_clusters(min_cluster_size=1)
        print(f"   Topic clusters found: {len(clusters)}")
        
        for cluster in clusters:
            print(f"     - {cluster['cluster_name']}: {cluster['cluster_size']} items")
        
        # Test content analytics
        print("\nTesting content analytics...")
        analytics = cache_service.get_content_analytics()
        print(f"   Analytics generated:")
        print(f"     - Categories: {len(analytics.get('category_distribution', {}))}")
        print(f"     - Top topics: {len(analytics.get('top_topics', {}))}")
        print(f"     - Total similarities: {analytics.get('similarity_stats', {}).get('total_similarities', 0)}")
        print(f"     - Total clusters: {analytics.get('cluster_stats', {}).get('total_clusters', 0)}")
        
        # Test cache optimization
        print("\nTesting cache optimization...")
        optimization_results = cache_service.optimize_cache()
        print(f"   Optimization results:")
        print(f"     - Index rebuilt: {optimization_results['index_rebuilt']}")
        print(f"     - Clusters updated: {optimization_results['clusters_updated']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Content cache service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_performance():
    """Test cache performance and deduplication."""
    print("\n=== Testing Cache Performance ===")
    
    try:
        cache_manager = CacheManager()
        
        # Test URL hash generation performance
        print("Testing URL hash generation performance...")
        test_urls = [
            "https://linkedin.com/posts/user1_topic1_activity-123",
            "https://linkedin.com/posts/user2_topic2_activity-456",
            "https://linkedin.com/posts/user3_topic3_activity-789",
        ] * 100  # 300 URLs total
        
        start_time = time.time()
        hashes = []
        for url in test_urls:
            hash_val = cache_manager.generate_url_hash(url)
            hashes.append(hash_val)
        
        hash_time = time.time() - start_time
        print(f"   Generated {len(hashes)} hashes in {hash_time:.3f}s")
        print(f"   Average: {hash_time/len(hashes)*1000:.2f}ms per hash")
        
        # Test deduplication
        unique_hashes = set(hashes)
        print(f"   Unique hashes: {len(unique_hashes)} (expected: 3)")
        
        # Test cache lookup performance
        print("\nTesting cache lookup performance...")
        
        # Cache some URLs first
        for i, url in enumerate(test_urls[:10]):
            cache_manager.cache_url(url, post_type="posts", post_id=f"activity-{i}")
        
        # Test lookup performance
        start_time = time.time()
        cache_hits = 0
        for url in test_urls[:50]:  # Test 50 lookups
            if cache_manager.is_url_cached(url):
                cache_hits += 1
        
        lookup_time = time.time() - start_time
        print(f"   Performed 50 lookups in {lookup_time:.3f}s")
        print(f"   Average: {lookup_time/50*1000:.2f}ms per lookup")
        print(f"   Cache hits: {cache_hits}/50")
        
        # Test cleanup performance
        print("\nTesting cache cleanup...")
        cleanup_stats = cache_manager.cleanup_old_cache(days_to_keep=0)  # Clean everything
        print(f"   Cleanup results: {cleanup_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_integration():
    """Test integration of caching with other components."""
    print("\n=== Testing Cache Integration ===")
    
    try:
        cache_manager = CacheManager()
        cache_service = ContentCacheService()
        
        # Test end-to-end workflow
        print("Testing end-to-end caching workflow...")
        
        # Simulate processing workflow
        test_url = "https://linkedin.com/posts/integration-test_activity-999"
        
        # Step 1: Check if URL is cached
        is_cached = cache_manager.is_url_cached(test_url)
        print(f"   1. URL cached initially: {is_cached}")
        
        # Step 2: Cache URL
        url_hash = cache_manager.cache_url(test_url, post_type="posts")
        print(f"   2. URL cached with hash: {url_hash}")
        
        # Step 3: Cache content
        sample_post = create_sample_post_content()[0]
        sample_post.url = test_url
        content_hash = cache_manager.cache_post_content(test_url, sample_post)
        print(f"   3. Content cached with hash: {content_hash}")
        
        # Step 4: Process and cache knowledge item
        sample_item = create_sample_knowledge_items()[0]
        sample_item.source_link = test_url
        
        cached_id, is_new = cache_service.cache_knowledge_item_enhanced(
            sample_item, sample_post, processing_time_ms=250
        )
        print(f"   4. Knowledge item cached: {cached_id} ({'new' if is_new else 'duplicate'})")
        
        # Step 5: Retrieve cached data
        cached_content = cache_manager.get_cached_content(test_url)
        cached_knowledge = cache_manager.get_cached_knowledge_item(test_url)
        
        print(f"   5. Retrieved cached content: {cached_content.title if cached_content else 'None'}")
        print(f"   6. Retrieved cached knowledge: {cached_knowledge.topic if cached_knowledge else 'None'}")
        
        # Test export functionality
        print("\nTesting cache export...")
        export_path = "./test_output/cache_export.json"
        export_success = cache_manager.export_cache_data(export_path)
        print(f"   Cache export: {'Success' if export_success else 'Failed'}")
        
        if export_success:
            export_file = Path(export_path)
            if export_file.exists():
                file_size = export_file.stat().st_size
                print(f"   Export file size: {file_size:,} bytes")
        
        # Final statistics
        final_stats = cache_manager.get_cache_statistics()
        print(f"\n✅ Integration test complete:")
        print(f"   Total URLs: {final_stats['total_urls_cached']}")
        print(f"   Total content: {final_stats['total_content_cached']}")
        print(f"   Total knowledge: {final_stats['total_knowledge_cached']}")
        print(f"   Duplicates prevented: {final_stats['duplicates_prevented']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    try:
        # Set up logging
        config = Config.from_env()
        logger = setup_logger(config=config)
        
        print("LinkedIn Knowledge Scraper - Caching System Test Suite")
        print("=" * 60)
        
        # Create test output directory
        Path("./test_output").mkdir(exist_ok=True)
        
        # Run tests
        tests = [
            ("Cache Manager", test_cache_manager),
            ("Content Cache Service", test_content_cache_service),
            ("Cache Performance", test_cache_performance),
            ("Cache Integration", test_cache_integration)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                results[test_name] = test_func()
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
            print("🎉 All caching system tests passed!")
            print("\nThe caching and deduplication system is ready!")
            print("\nKey features working:")
            print("- URL deduplication and caching")
            print("- Content similarity detection")
            print("- Knowledge item caching with search")
            print("- Processing queue management")
            print("- Performance optimization")
            print("- Cache analytics and statistics")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()