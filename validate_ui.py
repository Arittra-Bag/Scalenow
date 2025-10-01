#!/usr/bin/env python3
"""
Validation script for the LinkedIn Knowledge Management System web UI.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_ui_components():
    """Validate all UI components and functionality."""
    
    print("🔍 LinkedIn Knowledge Management System - UI Validation")
    print("=" * 60)
    
    results = {
        "templates": False,
        "static_files": False,
        "javascript": False,
        "css": False,
        "navigation": False
    }
    
    # 1. Test Templates
    print("\n📄 Testing HTML Templates...")
    try:
        from jinja2 import Environment, FileSystemLoader
        
        templates_dir = Path("linkedin_scraper/api/templates")
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        
        # Mock data
        mock_data = {
            "request": type('MockRequest', (), {
                'url': type('MockURL', (), {'path': '/'})()
            })(),
            "queue_status": {
                "total_tasks": 10,
                "queued_tasks": 3,
                "is_processing": False,
                "status_distribution": {"queued": 3, "completed": 5, "failed": 2},
                "stats": {"total_tasks": 10, "completed_tasks": 5, "failed_tasks": 2, "retried_tasks": 1}
            },
            "cache_stats": {"total_knowledge_cached": 25, "cache_hit_rate": 85.5, "database_size_mb": 12.3},
            "recent_items": [],
            "total_items": 25,
            "analytics": {"content_analytics": {"category_distribution": {}, "top_topics": {}, "course_references": {}}},
            "title": "Test",
            "datetime": datetime
        }
        
        templates = ["dashboard.html", "knowledge.html", "queue.html", "analytics.html", "upload.html"]
        
        for template_name in templates:
            template = env.get_template(template_name)
            rendered = template.render(**mock_data)
            print(f"   ✅ {template_name} - OK ({len(rendered):,} chars)")
        
        results["templates"] = True
        print("   📄 Templates: ✅ PASS")
        
    except Exception as e:
        print(f"   📄 Templates: ❌ FAIL - {e}")
    
    # 2. Test Static Files
    print("\n📁 Testing Static Files...")
    try:
        css_file = Path("linkedin_scraper/api/static/css/custom.css")
        if css_file.exists():
            size = css_file.stat().st_size
            print(f"   ✅ custom.css - OK ({size:,} bytes)")
            results["static_files"] = True
            results["css"] = True
            print("   📁 Static Files: ✅ PASS")
        else:
            print("   📁 Static Files: ❌ FAIL - CSS file missing")
    except Exception as e:
        print(f"   📁 Static Files: ❌ FAIL - {e}")
    
    # 3. Test JavaScript Functions
    print("\n🔧 Testing JavaScript Components...")
    try:
        base_template = Path("linkedin_scraper/api/templates/base.html")
        if base_template.exists():
            content = base_template.read_text()
            
            # Check for key JavaScript functions
            js_functions = [
                "apiCall",
                "showAlert", 
                "formatDate",
                "getStatusBadgeClass",
                "refreshData"
            ]
            
            missing_functions = []
            for func in js_functions:
                if f"function {func}" in content or f"{func} =" in content:
                    print(f"   ✅ {func}() - Found")
                else:
                    missing_functions.append(func)
                    print(f"   ❌ {func}() - Missing")
            
            if not missing_functions:
                results["javascript"] = True
                print("   🔧 JavaScript: ✅ PASS")
            else:
                print(f"   🔧 JavaScript: ❌ FAIL - Missing: {missing_functions}")
        
    except Exception as e:
        print(f"   🔧 JavaScript: ❌ FAIL - {e}")
    
    # 4. Test Navigation Structure
    print("\n🧭 Testing Navigation...")
    try:
        base_template = Path("linkedin_scraper/api/templates/base.html")
        if base_template.exists():
            content = base_template.read_text()
            
            # Check for navigation links
            nav_links = [
                ('Dashboard', '/'),
                ('Upload URLs', '/upload'),
                ('Processing Queue', '/queue'),
                ('Knowledge Repository', '/knowledge'),
                ('Analytics', '/analytics')
            ]
            
            missing_links = []
            for name, path in nav_links:
                if f'href="{path}"' in content:
                    print(f"   ✅ {name} ({path}) - Found")
                else:
                    missing_links.append((name, path))
                    print(f"   ❌ {name} ({path}) - Missing")
            
            if not missing_links:
                results["navigation"] = True
                print("   🧭 Navigation: ✅ PASS")
            else:
                print(f"   🧭 Navigation: ❌ FAIL - Missing: {missing_links}")
        
    except Exception as e:
        print(f"   🧭 Navigation: ❌ FAIL - {e}")
    
    # 5. Test Key Features
    print("\n⚙️  Testing Key Features...")
    
    feature_tests = [
        ("URL Upload Form", "upload.html", "addSingleUrl"),
        ("Knowledge Search", "knowledge.html", "searchKnowledge"),
        ("Queue Management", "queue.html", "startProcessing"),
        ("Analytics Charts", "analytics.html", "Chart"),
        ("Export Functions", "base.html", "export")
    ]
    
    feature_results = []
    
    for feature_name, template_file, search_term in feature_tests:
        try:
            template_path = Path(f"linkedin_scraper/api/templates/{template_file}")
            if template_path.exists():
                content = template_path.read_text()
                if search_term.lower() in content.lower():
                    print(f"   ✅ {feature_name} - Found")
                    feature_results.append(True)
                else:
                    print(f"   ❌ {feature_name} - Missing")
                    feature_results.append(False)
            else:
                print(f"   ❌ {feature_name} - Template missing")
                feature_results.append(False)
        except Exception as e:
            print(f"   ❌ {feature_name} - Error: {e}")
            feature_results.append(False)
    
    features_pass = all(feature_results)
    print(f"   ⚙️  Key Features: {'✅ PASS' if features_pass else '❌ FAIL'}")
    
    # Final Results
    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS:")
    print("=" * 60)
    
    for component, status in results.items():
        status_text = "✅ PASS" if status else "❌ FAIL"
        print(f"{component.replace('_', ' ').title():<20} {status_text}")
    
    print(f"Key Features:<20> {'✅ PASS' if features_pass else '❌ FAIL'}")
    
    overall_pass = all(results.values()) and features_pass
    
    print("=" * 60)
    print(f"🎯 OVERALL RESULT: {'✅ READY FOR TESTING' if overall_pass else '❌ NEEDS FIXES'}")
    
    if overall_pass:
        print("\n🚀 The web UI is ready for testing!")
        print("   You can now:")
        print("   1. Run 'python simple_test_server.py' to test the interface")
        print("   2. Move on to implementing task 7.3 (search and filtering)")
        print("   3. Test the complete workflow")
    else:
        print("\n🔧 Please fix the issues above before proceeding.")
    
    return overall_pass

def main():
    """Run the validation."""
    try:
        success = validate_ui_components()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())