#!/usr/bin/env python3
"""
Test script to validate HTML templates without running the full server.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from jinja2 import Environment, FileSystemLoader, TemplateError
    from datetime import datetime
    
    def test_templates():
        """Test all HTML templates for syntax errors."""
        templates_dir = Path("linkedin_scraper/api/templates")
        
        if not templates_dir.exists():
            print(f"❌ Templates directory not found: {templates_dir}")
            return False
        
        # Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        
        # Mock data for template testing
        mock_data = {
            "request": type('MockRequest', (), {
                'url': type('MockURL', (), {'path': '/'})()
            })(),
            "queue_status": {
                "total_tasks": 10,
                "queued_tasks": 3,
                "is_processing": False,
                "status_distribution": {
                    "queued": 3,
                    "completed": 5,
                    "failed": 2
                },
                "stats": {
                    "total_tasks": 10,
                    "completed_tasks": 5,
                    "failed_tasks": 2,
                    "retried_tasks": 1
                }
            },
            "cache_stats": {
                "total_knowledge_cached": 25,
                "cache_hit_rate": 85.5,
                "database_size_mb": 12.3
            },
            "recent_items": [
                {
                    "id": "test-1",
                    "post_title": "Test Knowledge Item",
                    "topic": "AI & Machine Learning",
                    "category": {"value": "AI & Machine Learning"},
                    "key_knowledge_content": "This is test knowledge content.",
                    "source_url": "https://linkedin.com/posts/test",
                    "created_at": datetime.now(),
                    "course_references": ["Course 1"],
                    "images": []
                }
            ],
            "total_items": 25,
            "analytics": {
                "content_analytics": {
                    "category_distribution": {
                        "AI & Machine Learning": 10,
                        "SaaS & Business": 8,
                        "Marketing & Sales": 7
                    },
                    "top_topics": {
                        "Machine Learning": 5,
                        "Business Strategy": 4,
                        "Sales Techniques": 3
                    },
                    "course_references": {
                        "AI Fundamentals": 3,
                        "Business 101": 2
                    }
                }
            },
            "title": "Test Page",
            "datetime": datetime
        }
        
        # List of templates to test
        templates_to_test = [
            "base.html",
            "dashboard.html", 
            "knowledge.html",
            "queue.html",
            "analytics.html",
            "upload.html"
        ]
        
        print("🧪 Testing HTML templates...")
        print("=" * 50)
        
        all_passed = True
        
        for template_name in templates_to_test:
            try:
                template = env.get_template(template_name)
                
                # Try to render the template
                if template_name == "base.html":
                    # Base template needs minimal data
                    rendered = template.render(request=mock_data["request"])
                else:
                    # Other templates extend base and need more data
                    rendered = template.render(**mock_data)
                
                print(f"✅ {template_name:<20} - OK ({len(rendered):,} chars)")
                
            except TemplateError as e:
                print(f"❌ {template_name:<20} - Template Error: {e}")
                all_passed = False
            except Exception as e:
                print(f"❌ {template_name:<20} - Error: {e}")
                all_passed = False
        
        print("=" * 50)
        
        if all_passed:
            print("🎉 All templates passed validation!")
            return True
        else:
            print("💥 Some templates have errors. Please fix them before testing.")
            return False
    
    def check_static_files():
        """Check if static files exist."""
        print("\n📁 Checking static files...")
        print("=" * 50)
        
        static_files = [
            "linkedin_scraper/api/static/css/custom.css"
        ]
        
        all_exist = True
        
        for file_path in static_files:
            path = Path(file_path)
            if path.exists():
                size = path.stat().st_size
                print(f"✅ {file_path:<40} - OK ({size:,} bytes)")
            else:
                print(f"❌ {file_path:<40} - Missing")
                all_exist = False
        
        print("=" * 50)
        
        if all_exist:
            print("📂 All static files found!")
        else:
            print("📂 Some static files are missing.")
        
        return all_exist
    
    def main():
        """Run all template tests."""
        print("LinkedIn Knowledge Management System - Template Validator")
        print("=" * 60)
        
        templates_ok = test_templates()
        static_ok = check_static_files()
        
        print(f"\n📊 Test Results:")
        print(f"Templates: {'✅ PASS' if templates_ok else '❌ FAIL'}")
        print(f"Static Files: {'✅ PASS' if static_ok else '❌ FAIL'}")
        
        if templates_ok and static_ok:
            print("\n🚀 Ready to test the web interface!")
            print("Run: python test_server.py")
        else:
            print("\n🔧 Please fix the issues above before testing.")
            return 1
        
        return 0
    
    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required dependencies:")
    print("pip install jinja2")
    sys.exit(1)