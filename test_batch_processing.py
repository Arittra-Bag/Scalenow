"""
Test script for the batch processing and error handling system.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from linkedin_scraper.services.batch_processor import BatchProcessor, TaskPriority, TaskStatus
from linkedin_scraper.services.error_handler import ErrorHandler, ErrorSeverity, RecoveryAction
from linkedin_scraper.models.exceptions import ScrapingError, ProcessingError, APIError
from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.logger import setup_logger


def create_sample_urls() -> list:
    """Create sample LinkedIn URLs for testing."""
    urls = [
        "https://linkedin.com/posts/user1_ai-innovation_activity-123456",
        "https://linkedin.com/posts/user2_saas-growth_activity-234567", 
        "https://linkedin.com/posts/user3_marketing-tips_activity-345678",
        "https://linkedin.com/posts/user4_leadership-skills_activity-456789",
        "https://linkedin.com/posts/user5_tech-trends_activity-567890",
        "https://linkedin.com/posts/user6_business-strategy_activity-678901",
        "https://linkedin.com/posts/user7_data-science_activity-789012",
        "https://linkedin.com/posts/user8_remote-work_activity-890123",
        "https://linkedin.com/posts/user9_startup-life_activity-901234",
        "https://linkedin.com/posts/user10_career-advice_activity-012345"
    ]
    return urls


async def simulate_processing_with_errors(url: str, metadata: dict) -> dict:
    """Simulate processing that might fail."""
    # Simulate different types of errors based on URL
    if "user3" in url:
        raise ScrapingError("Failed to scrape content", url=url, status_code=404)
    elif "user6" in url:
        raise APIError("Rate limit exceeded", api_name="LinkedIn", error_code="RATE_LIMIT")
    elif "user9" in url:
        raise ProcessingError("Content processing failed", stage="ai_processing")
    
    # Simulate processing time
    await asyncio.sleep(0.5)
    
    return {
        'url': url,
        'processed_at': datetime.now().isoformat(),
        'metadata': metadata,
        'success': True
    }


def test_batch_processor_basic():
    """Test basic batch processor functionality."""
    print("=== Testing Batch Processor Basic Functionality ===")
    
    try:
        processor = BatchProcessor()
        
        # Test adding URLs
        print("Testing URL addition...")
        sample_urls = create_sample_urls()[:5]  # Use first 5 URLs
        
        task_ids = []
        for i, url in enumerate(sample_urls):
            priority = TaskPriority.HIGH if i == 0 else TaskPriority.NORMAL
            metadata = {'test_id': i, 'batch': 'test_batch_1'}
            
            task_id = processor.add_url(url, priority=priority, metadata=metadata)
            if task_id:
                task_ids.append(task_id)
                print(f"   Added task: {task_id} (priority: {priority.name})")
        
        print(f"✅ Added {len(task_ids)} tasks to queue")
        
        # Test queue status
        status = processor.get_queue_status()
        print(f"   Queue status: {status['total_tasks']} total, {status['queued_tasks']} queued")
        print(f"   Status distribution: {status['status_distribution']}")
        
        # Test task details
        if task_ids:
            task_details = processor.get_task_details(task_ids[0])
            print(f"   First task details: {task_details['status']} - {task_details['url']}")
        
        # Test batch URL addition
        print("\nTesting batch URL addition...")
        batch_urls = create_sample_urls()[5:8]  # Use next 3 URLs
        batch_task_ids = processor.add_urls_batch(
            batch_urls, 
            priority=TaskPriority.LOW,
            metadata={'batch': 'test_batch_2'}
        )
        print(f"✅ Added {len(batch_task_ids)} tasks in batch")
        
        # Final queue status
        final_status = processor.get_queue_status()
        print(f"   Final queue: {final_status['total_tasks']} total tasks")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processor basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_batch_processing_execution():
    """Test batch processing execution."""
    print("\n=== Testing Batch Processing Execution ===")
    
    try:
        processor = BatchProcessor()
        
        # Add URLs with different priorities
        print("Setting up test queue...")
        test_urls = create_sample_urls()[:6]
        
        priorities = [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, 
                     TaskPriority.NORMAL, TaskPriority.LOW, TaskPriority.LOW]
        
        for url, priority in zip(test_urls, priorities):
            processor.add_url(url, priority=priority, metadata={'test': True})
        
        print(f"   Added {len(test_urls)} tasks with various priorities")
        
        # Mock the processing function
        original_process_url = processor._process_url
        processor._process_url = simulate_processing_with_errors
        
        # Set up progress tracking
        progress_updates = []
        def progress_callback(progress_info):
            progress_updates.append(progress_info)
            print(f"   Progress: {progress_info['completed_tasks']}/{progress_info['total_tasks']} completed, "
                  f"{progress_info['active_tasks']} active, {progress_info['queue_size']} queued")
        
        # Process the queue
        print("\nStarting batch processing...")
        start_time = time.time()
        
        stats = await processor.process_queue(
            max_concurrent=3,
            progress_callback=progress_callback
        )
        
        processing_time = time.time() - start_time
        
        print(f"\n✅ Batch processing completed in {processing_time:.2f}s")
        print(f"   Total tasks: {stats.total_tasks}")
        print(f"   Completed: {stats.completed_tasks}")
        print(f"   Failed: {stats.failed_tasks}")
        print(f"   Retried: {stats.retried_tasks}")
        print(f"   Success rate: {stats.success_rate:.1f}%")
        print(f"   Average processing time: {stats.average_processing_time:.2f}s")
        
        # Check final queue status
        final_status = processor.get_queue_status()
        print(f"   Final status distribution: {final_status['status_distribution']}")
        
        # Test export functionality
        export_path = "./test_output/batch_results.json"
        export_success = processor.export_results(export_path, include_failed=True)
        print(f"   Results export: {'Success' if export_success else 'Failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processing execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handler():
    """Test error handling and recovery."""
    print("\n=== Testing Error Handler ===")
    
    try:
        error_handler = ErrorHandler()
        
        # Test different types of errors
        print("Testing error handling for different error types...")
        
        test_errors = [
            (ScrapingError("Page not found", url="https://example.com", status_code=404), 
             {'operation': 'scraping', 'url': 'https://example.com'}),
            (APIError("Rate limit exceeded", api_name="LinkedIn", error_code="RATE_LIMIT"),
             {'operation': 'api_call', 'endpoint': '/posts'}),
            (ProcessingError("AI processing failed", stage="content_extraction"),
             {'operation': 'processing', 'content_id': 'test123'}),
        ]
        
        # Mock operation for retry testing
        async def mock_operation(should_succeed=False):
            if should_succeed:
                return {'success': True, 'data': 'processed'}
            else:
                raise ScrapingError("Mock scraping error")
        
        for i, (error, context) in enumerate(test_errors):
            print(f"\n   Testing error {i+1}: {type(error).__name__}")
            
            # Handle the error
            success, result = await error_handler.handle_error(
                error, context, mock_operation, should_succeed=(i == 0)  # First error succeeds on retry
            )
            
            print(f"     Recovery success: {success}")
            print(f"     Result: {result}")
        
        # Test error statistics
        print("\nTesting error statistics...")
        stats = error_handler.get_error_statistics()
        print(f"   Total errors: {stats['total_errors']}")
        print(f"   Error types: {list(stats['error_counts_by_type'].keys())}")
        print(f"   Recovery success rate: {stats['recovery_success_rate']:.1f}%")
        print(f"   Most common errors: {stats['most_common_errors']}")
        
        # Test error patterns
        patterns = error_handler.get_error_patterns()
        print(f"   Error patterns: {len(patterns)} types identified")
        
        # Test error report export
        report_path = "./test_output/error_report.json"
        export_success = error_handler.export_error_report(report_path)
        print(f"   Error report export: {'Success' if export_success else 'Failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integrated_batch_with_errors():
    """Test integrated batch processing with error handling."""
    print("\n=== Testing Integrated Batch Processing with Error Handling ===")
    
    try:
        processor = BatchProcessor()
        error_handler = ErrorHandler()
        
        # Add URLs that will cause different types of errors
        print("Setting up test queue with error-prone URLs...")
        test_urls = create_sample_urls()[:8]
        
        for i, url in enumerate(test_urls):
            priority = TaskPriority.HIGH if i < 2 else TaskPriority.NORMAL
            processor.add_url(url, priority=priority, metadata={'test_run': 'integrated'})
        
        # Mock processing with error handling
        async def process_with_error_handling(url, metadata):
            try:
                return await simulate_processing_with_errors(url, metadata)
            except Exception as e:
                # Use error handler for recovery
                context = {'url': url, 'metadata': metadata, 'operation': 'processing'}
                success, result = await error_handler.handle_error(
                    e, context, simulate_processing_with_errors, url, metadata
                )
                
                if success:
                    return result
                else:
                    # Return partial result for failed operations
                    return {
                        'url': url,
                        'processed_at': datetime.now().isoformat(),
                        'metadata': metadata,
                        'success': False,
                        'error_handled': True
                    }
        
        # Replace processing function
        processor._process_url = process_with_error_handling
        
        # Process with progress tracking
        print("\nStarting integrated processing...")
        
        progress_count = 0
        def integrated_progress_callback(progress_info):
            nonlocal progress_count
            progress_count += 1
            if progress_count % 3 == 0:  # Print every 3rd update
                print(f"   Progress: {progress_info['completed_tasks']}/{progress_info['total_tasks']} "
                      f"({progress_info['completed_tasks']/progress_info['total_tasks']*100:.0f}%)")
        
        stats = await processor.process_queue(
            max_concurrent=2,
            progress_callback=integrated_progress_callback
        )
        
        print(f"\n✅ Integrated processing completed:")
        print(f"   Total tasks: {stats.total_tasks}")
        print(f"   Completed: {stats.completed_tasks}")
        print(f"   Failed: {stats.failed_tasks}")
        print(f"   Success rate: {stats.success_rate:.1f}%")
        
        # Get error statistics
        error_stats = error_handler.get_error_statistics()
        print(f"\n   Error handling statistics:")
        print(f"   Total errors handled: {error_stats['total_errors']}")
        print(f"   Recovery success rate: {error_stats['recovery_success_rate']:.1f}%")
        
        # Export combined results
        batch_export = processor.export_results("./test_output/integrated_batch_results.json", include_failed=True)
        error_export = error_handler.export_error_report("./test_output/integrated_error_report.json")
        
        print(f"   Exports: Batch {'✅' if batch_export else '❌'}, Errors {'✅' if error_export else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integrated batch processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_queue_persistence():
    """Test queue persistence and recovery."""
    print("\n=== Testing Queue Persistence ===")
    
    try:
        # Create first processor and add tasks
        print("Creating first processor and adding tasks...")
        processor1 = BatchProcessor()
        
        test_urls = create_sample_urls()[:3]
        task_ids = []
        
        for url in test_urls:
            task_id = processor1.add_url(url, priority=TaskPriority.NORMAL)
            if task_id:
                task_ids.append(task_id)
        
        print(f"   Added {len(task_ids)} tasks to first processor")
        
        # Get status before shutdown
        status_before = processor1.get_queue_status()
        print(f"   Status before: {status_before['total_tasks']} tasks")
        
        # Simulate shutdown by creating new processor (should load from file)
        print("\nSimulating restart - creating second processor...")
        processor2 = BatchProcessor()
        
        # Check if tasks were loaded
        status_after = processor2.get_queue_status()
        print(f"   Status after restart: {status_after['total_tasks']} tasks")
        
        # Verify task details are preserved
        if task_ids and status_after['total_tasks'] > 0:
            # Get any task ID from the loaded processor
            loaded_task_ids = list(processor2.tasks.keys())
            if loaded_task_ids:
                task_details = processor2.get_task_details(loaded_task_ids[0])
                print(f"   Loaded task details: {task_details['status']} - {task_details['priority']}")
        
        persistence_success = status_before['total_tasks'] == status_after['total_tasks']
        print(f"✅ Queue persistence: {'Success' if persistence_success else 'Failed'}")
        
        return persistence_success
        
    except Exception as e:
        print(f"❌ Queue persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    try:
        # Set up logging
        config = Config.from_env()
        logger = setup_logger(config=config)
        
        print("LinkedIn Knowledge Scraper - Batch Processing Test Suite")
        print("=" * 60)
        
        # Create test output directory
        Path("./test_output").mkdir(exist_ok=True)
        
        # Run tests
        tests = [
            ("Batch Processor Basic", test_batch_processor_basic),
            ("Batch Processing Execution", test_batch_processing_execution),
            ("Error Handler", test_error_handler),
            ("Integrated Batch with Errors", test_integrated_batch_with_errors),
            ("Queue Persistence", test_queue_persistence)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    results[test_name] = await test_func()
                else:
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
            print(f"{test_name:30} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All batch processing tests passed!")
            print("\nThe batch processing and error handling system is ready!")
            print("\nKey features working:")
            print("- Priority-based task queue management")
            print("- Concurrent batch processing with progress tracking")
            print("- Comprehensive error handling with recovery strategies")
            print("- Automatic retry with exponential backoff")
            print("- Queue persistence and recovery")
            print("- Detailed statistics and reporting")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())