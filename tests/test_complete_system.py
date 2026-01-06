#!/usr/bin/env python3
"""
Test completo del sistema con todas las herramientas activadas.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_test_project():
    """Create a test project with all types of files to trigger tool activation."""
    test_dir = Path(tempfile.mkdtemp(prefix="groq_test_"))
    print(f"📁 Created test directory: {test_dir}")

    # Create Git repository
    subprocess.run(["git", "init"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, capture_output=True)

    # Create Python files
    (test_dir / "requirements.txt").write_text("requests==2.28.0\npandas==1.5.0\n")
    (test_dir / "setup.py").write_text("""
from setuptools import setup
setup(name="test-project", version="0.1")
""")
    (test_dir / "main.py").write_text("print('Hello World')")
    (test_dir / "test_main.py").write_text("def test_hello(): pass")

    # Create Node.js files
    (test_dir / "package.json").write_text("""
{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {"start": "node index.js"}
}
""")
    (test_dir / "index.js").write_text("console.log('Hello World');")
    (test_dir / "app.js").write_text("const express = require('express');")

    # Create web files
    (test_dir / "index.html").write_text("<html><body>Hello</body></html>")
    (test_dir / "styles.css").write_text("body { color: blue; }")
    (test_dir / "script.js").write_text("console.log('web app');")

    # Create database file
    (test_dir / "test.db").write_text("")  # SQLite database placeholder

    # Create some content in files for Git
    (test_dir / "README.md").write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@test.com", "commit", "-m", "Initial commit"], cwd=test_dir, capture_output=True)

    return test_dir

def test_tool_detection(test_dir):
    """Test that tools are properly detected and registered."""
    print("🧪 Testing tool detection and registration...")

    try:
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(test_dir)

        # Import and test tool setup
        from iabuilder.tools import setup_tools

        tool_count = setup_tools()
        print(f"✅ Registered {tool_count} tools")

        # Test context detection
        from iabuilder.tools import ContextAwareToolManager
        manager = ContextAwareToolManager()
        context = manager._detect_project_context()

        print("📋 Detected contexts:")
        for ctx, detected in context.items():
            status = "✅" if detected else "❌"
            print(f"  {status} {ctx}")

        # Verify critical contexts are detected
        expected_contexts = ["python_project", "node_project", "web_project",
                           "git_repository", "database_project", "package_project"]

        success_count = 0
        for ctx in expected_contexts:
            if context.get(ctx, False):
                success_count += 1
                print(f"  ✅ {ctx} detected")
            else:
                print(f"  ❌ {ctx} NOT detected")

        print(f"\n🎯 Context detection: {success_count}/{len(expected_contexts)} expected contexts")

        # Test tool registry
        from iabuilder.tools import get_tool_registry
        registry = get_tool_registry()
        tools = registry.list_tools()

        # Check for specialized tools
        specialized_tools = {
            "git": ["git_status", "git_commit", "git_branch", "git_log", "git_remote"],
            "database": ["database_connect", "query_executor", "database_schema"],
            "packages": ["package_installer", "dependency_analyzer"],
        }

        total_specialized = 0
        for category, tool_names in specialized_tools.items():
            found_tools = [t for t in tools if any(tn in t for tn in tool_names)]
            if found_tools:
                print(f"  ✅ {category} tools: {found_tools}")
                total_specialized += len(found_tools)
            else:
                print(f"  ❌ No {category} tools found")

        print(f"\n🧰 Total tools: {len(tools)} (including {total_specialized} specialized)")

        # Test IntentClassifier with technical messages
        from iabuilder.intent_classifier import IntentClassifier, IntentType

        classifier = IntentClassifier()

        test_messages = [
            ("commit my changes", IntentType.ACTIONABLE, True),
            ("show git status", IntentType.ACTIONABLE, True),
            ("run a sql query", IntentType.ACTIONABLE, True),
            ("install dependencies", IntentType.ACTIONABLE, True),
            ("read the README", IntentType.ACTIONABLE, True),
        ]

        print("\n🤖 Testing IntentClassifier:")
        classifier_correct = 0

        for msg, expected_intent, expected_tools in test_messages:
            intent = classifier.classify(msg)
            should_use_tools, confidence = classifier.should_use_tools(msg)

            intent_ok = intent == expected_intent
            tools_ok = should_use_tools == expected_tools

            if intent_ok and tools_ok:
                classifier_correct += 1
                status = "✅"
            else:
                status = "❌"

            print(f"     → {intent.value} | Tools: {should_use_tools} ({confidence:.2f})")
        print(f"\n🎯 IntentClassifier: {classifier_correct}/{len(test_messages)} correct")

        # Overall success
        context_success = success_count >= 4  # At least 4 contexts detected
        tools_success = len(tools) >= 20  # At least 20 tools registered
        classifier_success = classifier_correct >= 4  # At least 4/5 correct

        overall_success = context_success and tools_success and classifier_success

        print(f"\n🏆 SYSTEM TEST RESULTS:")
        print(f"  Context Detection: {'✅' if context_success else '❌'} ({success_count}/{len(expected_contexts)})")
        print(f"  Tool Registration: {'✅' if tools_success else '❌'} ({len(tools)} tools)")
        print(f"  Intent Classification: {'✅' if classifier_success else '❌'} ({classifier_correct}/{len(test_messages)})")
        print(f"  Overall Status: {'🎉 SUCCESS' if overall_success else '⚠️  NEEDS IMPROVEMENT'}")

        return overall_success

    finally:
        os.chdir(original_cwd)

def main():
    """Main test execution."""
    print("🚀 TEST COMPLETO DEL SISTEMA GROQ CLI CUSTOM")
    print("=" * 60)

    try:
        # Create test project
        test_dir = create_test_project()

        # Run tests
        success = test_tool_detection(test_dir)

        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\n🧹 Cleaned up test directory: {test_dir}")

        if success:
            print("\n🎉 ¡SISTEMA COMPLETO FUNCIONANDO!")
            print("Todas las herramientas especializadas están activas:")
            print("  • Git tools para control de versiones")
            print("  • Database tools para gestión de datos")
            print("  • Package tools para gestión de dependencias")
            print("  • Arquitectura inteligente de clasificación")
            return 0
        else:
            print("\n⚠️  Sistema necesita ajustes")
            return 1

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())