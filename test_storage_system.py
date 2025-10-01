"""
Test script for the storage and file management system.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from linkedin_scraper.storage.repository_models import KnowledgeRepository, RepositoryManager
from linkedin_scraper.storage.excel_generator import ExcelGenerator
from linkedin_scraper.storage.word_generator import WordGenerator
from linkedin_scraper.storage.file_organizer import FileOrganizer
from linkedin_scraper.models.knowledge_item import KnowledgeItem, Category
from linkedin_scraper.models.post_content import ImageData
from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.logger import setup_logger


def create_sample_knowledge_items() -> list:
    """Create sample knowledge items for testing."""
    items = [
        KnowledgeItem(
            topic="AI in Business",
            post_title="How AI is Transforming Customer Service",
            key_knowledge_content="AI chatbots can handle 80% of customer inquiries automatically, reducing response time by 60% and improving customer satisfaction scores by 25%.",
            infographic_summary="Chart showing AI adoption rates across industries",
            source_link="https://linkedin.com/posts/ai-expert-customer-service",
            notes_applications="Implement AI chatbots for tier-1 support, maintain human oversight for complex issues",
            category=Category.AI_MACHINE_LEARNING,
            course_references=["AI for Customer Service Certification", "Machine Learning Fundamentals"]
        ),
        KnowledgeItem(
            topic="SaaS Growth",
            post_title="SaaS Metrics That Matter in 2024",
            key_knowledge_content="Key SaaS metrics: Monthly Recurring Revenue (MRR), Customer Acquisition Cost (CAC), Lifetime Value (LTV), and Churn Rate. Aim for LTV:CAC ratio of 3:1 or higher.",
            infographic_summary="Dashboard showing key SaaS metrics and benchmarks",
            source_link="https://linkedin.com/posts/saas-expert-metrics-2024",
            notes_applications="Track these metrics monthly, focus on reducing churn through better onboarding",
            category=Category.SAAS_BUSINESS,
            course_references=["SaaS Business Model Mastery"]
        ),
        KnowledgeItem(
            topic="Digital Marketing",
            post_title="Email Marketing Best Practices",
            key_knowledge_content="Personalized email campaigns see 26% higher open rates. Segmentation can improve click-through rates by 100%. A/B testing subject lines increases engagement by 15%.",
            infographic_summary="Email marketing statistics and best practices infographic",
            source_link="https://linkedin.com/posts/marketing-guru-email-tips",
            notes_applications="Implement email segmentation, test subject lines regularly, personalize content",
            category=Category.MARKETING_SALES,
            course_references=["Advanced Email Marketing", "Digital Marketing Analytics"]
        ),
        KnowledgeItem(
            topic="Leadership",
            post_title="Remote Team Management Strategies",
            key_knowledge_content="Effective remote leadership requires clear communication, regular check-ins, and trust-building. Use asynchronous communication for 70% of interactions, synchronous for critical decisions.",
            infographic_summary="Remote team management framework diagram",
            source_link="https://linkedin.com/posts/leadership-coach-remote-teams",
            notes_applications="Schedule weekly 1:1s, use project management tools, establish clear expectations",
            category=Category.LEADERSHIP_MANAGEMENT,
            course_references=["Remote Leadership Certification"]
        ),
        KnowledgeItem(
            topic="Cloud Computing",
            post_title="Microservices Architecture Benefits",
            key_knowledge_content="Microservices can improve deployment frequency by 200x, reduce lead time by 2400x, and increase system reliability. However, they add complexity in monitoring and debugging.",
            infographic_summary="Microservices vs monolithic architecture comparison",
            source_link="https://linkedin.com/posts/tech-architect-microservices",
            notes_applications="Start with monolith, migrate to microservices when team size exceeds 8-10 people",
            category=Category.TECHNOLOGY_TRENDS,
            course_references=["Microservices Design Patterns", "Cloud Architecture Fundamentals"]
        )
    ]
    
    return items


def test_repository_models():
    """Test the knowledge repository and repository manager."""
    print("=== Testing Repository Models ===")
    
    try:
        # Create sample items
        items = create_sample_knowledge_items()
        
        # Create repository
        repository = KnowledgeRepository(
            items=items,
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        print(f"✅ Repository created with {len(repository.items)} items")
        print(f"   Categories: {len(repository.metadata.get('categories', {}))}")
        print(f"   Date range: {repository.metadata.get('date_range', {})}")
        
        # Test repository operations
        ai_items = repository.get_items_by_category(Category.AI_MACHINE_LEARNING)
        print(f"   AI items: {len(ai_items)}")
        
        search_results = repository.search_items("email")
        print(f"   Search results for 'email': {len(search_results)}")
        
        # Test serialization
        json_data = repository.to_json()
        restored_repo = KnowledgeRepository.from_json(json_data)
        print(f"✅ Serialization test: {len(restored_repo.items)} items restored")
        
        # Test repository manager
        config = Config.from_env()
        repo_manager = RepositoryManager(config.knowledge_repo_path)
        
        # Save and load
        repo_manager.save_repository(repository)
        loaded_repo = repo_manager.load_repository()
        print(f"✅ Repository manager: {len(loaded_repo.items)} items loaded")
        
        # Get statistics
        stats = repo_manager.get_statistics()
        print(f"   Database stats: {stats.get('total_items', 0)} items")
        
        return True
        
    except Exception as e:
        print(f"❌ Repository models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_generator():
    """Test the Excel file generator."""
    print("\n=== Testing Excel Generator ===")
    
    try:
        # Create sample repository
        items = create_sample_knowledge_items()
        repository = KnowledgeRepository(
            items=items,
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create Excel generator
        excel_gen = ExcelGenerator()
        
        # Generate Excel file
        output_path = "./test_output/knowledge_repository.xlsx"
        result_path = excel_gen.generate_excel_file(
            repository=repository,
            output_path=output_path,
            include_metadata=True,
            include_statistics=True
        )
        
        print(f"✅ Excel file generated: {result_path}")
        
        # Check if file exists and has content
        excel_file = Path(result_path)
        if excel_file.exists():
            file_size = excel_file.stat().st_size
            print(f"   File size: {file_size:,} bytes")
            
            # Test simple Excel generation (fallback)
            simple_path = "./test_output/simple_knowledge.xlsx"
            simple_result = excel_gen.generate_simple_excel(repository, simple_path)
            print(f"✅ Simple Excel generated: {simple_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Excel generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_word_generator():
    """Test the Word document generator."""
    print("\n=== Testing Word Generator ===")
    
    try:
        # Create sample repository
        items = create_sample_knowledge_items()
        repository = KnowledgeRepository(
            items=items,
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create Word generator
        word_gen = WordGenerator()
        
        # Generate Word document
        output_path = "./test_output/knowledge_repository.docx"
        result_path = word_gen.generate_word_document(
            repository=repository,
            output_path=output_path,
            include_toc=True,
            include_metadata=True,
            group_by_category=True
        )
        
        print(f"✅ Word document generated: {result_path}")
        
        # Check if file exists and has content
        word_file = Path(result_path)
        if word_file.exists():
            file_size = word_file.stat().st_size
            print(f"   File size: {file_size:,} bytes")
            
            # Test summary document
            summary_path = "./test_output/knowledge_summary.docx"
            summary_result = word_gen.generate_summary_document(
                repository, summary_path, max_items_per_category=3
            )
            print(f"✅ Summary document generated: {summary_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Word generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_organizer():
    """Test the file system organizer."""
    print("\n=== Testing File Organizer ===")
    
    try:
        # Create file organizer
        file_org = FileOrganizer()
        
        print(f"✅ File organizer initialized: {file_org.base_path}")
        
        # Test folder structure creation
        file_org.create_folder_structure()
        print("✅ Folder structure created")
        
        # Create sample repository
        items = create_sample_knowledge_items()
        repository = KnowledgeRepository(
            items=items,
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test file organization
        date_org = file_org.organize_files_by_date(repository)
        print(f"✅ Date organization: {len(date_org)} periods")
        
        category_org = file_org.organize_files_by_category(repository)
        print(f"✅ Category organization: {len(category_org)} categories")
        
        # Test backup creation
        backup_path = file_org.create_backup(repository, backup_type="data_only")
        print(f"✅ Backup created: {backup_path}")
        
        # Test storage statistics
        stats = file_org.get_storage_statistics()
        print(f"✅ Storage stats: {stats.get('total_size_mb', 0):.2f} MB total")
        
        # Test file structure validation
        validation = file_org.validate_file_structure()
        print(f"✅ File structure validation: {'PASSED' if validation['valid'] else 'FAILED'}")
        if validation['issues']:
            print(f"   Issues: {len(validation['issues'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ File organizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration of all storage components."""
    print("\n=== Testing Storage Integration ===")
    
    try:
        # Create sample data
        items = create_sample_knowledge_items()
        repository = KnowledgeRepository(
            items=items,
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Initialize all components
        config = Config.from_env()
        repo_manager = RepositoryManager(config.knowledge_repo_path)
        excel_gen = ExcelGenerator(config)
        word_gen = WordGenerator(config)
        file_org = FileOrganizer(config)
        
        # Save repository
        repo_manager.save_repository(repository)
        print("✅ Repository saved")
        
        # Generate files
        excel_path = file_org.excels_path / "integrated_test.xlsx"
        word_path = file_org.docs_path / "integrated_test.docx"
        
        excel_gen.generate_excel_file(repository, str(excel_path))
        word_gen.generate_word_document(repository, str(word_path))
        print("✅ Files generated in organized structure")
        
        # Organize files
        file_org.organize_files_by_category(repository)
        file_org.organize_files_by_date(repository)
        print("✅ Files organized")
        
        # Create backup
        backup_path = file_org.create_backup(repository, "full")
        print(f"✅ Full backup created: {backup_path}")
        
        # Get final statistics
        storage_stats = file_org.get_storage_statistics()
        repo_stats = repo_manager.get_statistics()
        
        print(f"✅ Integration complete:")
        print(f"   Repository items: {repo_stats.get('total_items', 0)}")
        print(f"   Storage size: {storage_stats.get('total_size_mb', 0):.2f} MB")
        print(f"   Files created: {sum(storage_stats.get('file_counts', {}).values())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    try:
        # Set up logging
        config = Config.from_env()
        logger = setup_logger(config=config)
        
        print("LinkedIn Knowledge Scraper - Storage System Test Suite")
        print("=" * 60)
        
        # Create test output directory
        Path("./test_output").mkdir(exist_ok=True)
        
        # Run tests
        tests = [
            ("Repository Models", test_repository_models),
            ("Excel Generator", test_excel_generator),
            ("Word Generator", test_word_generator),
            ("File Organizer", test_file_organizer),
            ("Storage Integration", test_integration)
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
            print("🎉 All storage system tests passed!")
            print("\nThe storage and file management system is ready!")
            print("\nGenerated files can be found in:")
            print("- ./test_output/ (test files)")
            print("- ./knowledge_repository/ (organized structure)")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()