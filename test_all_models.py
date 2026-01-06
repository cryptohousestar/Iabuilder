#!/usr/bin/env python3
"""Comprehensive test of all models with all tools."""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_all_models_with_tools():
    """Test all available models with all tools."""
    print("🧪 TESTING ALL MODELS WITH ALL TOOLS")
    print("=" * 80)

    # Set API key from environment variable for testing
    # Users should set GROQ_API_KEY environment variable before running tests

    from iabuilder.client import GroqClient
    from iabuilder.tools import get_tool_registry, register_tool
    from iabuilder.tools.file_ops import ReadFileTool, WriteFileTool, EditFileTool
    from iabuilder.tools.bash import BashTool
    from iabuilder.tools.search import GrepSearchTool, GlobSearchTool
    from iabuilder.tools.web import WebSearchTool

    # Register all tools
    register_tool(ReadFileTool())
    register_tool(WriteFileTool())
    register_tool(EditFileTool())
    register_tool(BashTool())
    register_tool(GrepSearchTool())
    register_tool(GlobSearchTool())
    register_tool(WebSearchTool())

    client = GroqClient(api_key=os.environ['GROQ_API_KEY'])
    registry = get_tool_registry()
    tool_schemas = registry.get_schemas()

    # Get all models
    models = client.get_available_models()
    categories = client.categorize_models()

    print(f"📊 Total models to test: {len(models)}")
    print(f"🛠️  Tools registered: {len(tool_schemas)}")
    print()

    results = {}

    # Test each model
    for category, model_list in categories.items():
        if not model_list:
            continue

        print(f"🔹 Testing {category.upper()} models ({len(model_list)}):")
        print("-" * 60)

        for model_id in sorted(model_list):
            print(f"\n🧪 Testing: {model_id}")
            start_time = time.time()

            try:
                # Test basic function calling support
                supports_tools = client.test_function_calling(model_id)
                results[model_id] = {
                    'category': category,
                    'supports_function_calling': supports_tools,
                    'tools_tested': {},
                    'errors': []
                }

                if supports_tools:
                    print("  ✅ Supports function calling")

                    # Test each tool with a simple query
                    test_cases = {
                        'read_file': "Read the first line of requirements.txt",
                        'execute_bash': "Run 'echo hello world'",
                        'grep_search': "Find the word 'python' in all files",
                        'glob_search': "Find all .py files in the current directory",
                        'web_search': "Search for 'python programming' on the web"
                    }

                    for tool_name, query in test_cases.items():
                        try:
                            print(f"    🛠️  Testing {tool_name}...")
                            messages = [{"role": "user", "content": query}]

                            response = client.send_message(
                                messages=messages,
                                tools=tool_schemas,
                                max_tokens=1000,
                                temperature=0.1,
                                model=model_id
                            )

                            assistant_message = response.choices[0].message
                            tool_calls = assistant_message.tool_calls or []

                            if tool_calls:
                                results[model_id]['tools_tested'][tool_name] = 'success'
                                print(f"      ✅ {tool_name}: Generated {len(tool_calls)} tool call(s)")
                            else:
                                results[model_id]['tools_tested'][tool_name] = 'no_tools'
                                print(f"      ⚠️  {tool_name}: No tool calls generated")

                        except Exception as e:
                            results[model_id]['tools_tested'][tool_name] = f'error: {str(e)}'
                            results[model_id]['errors'].append(f"{tool_name}: {str(e)}")
                            print(f"      ❌ {tool_name}: {str(e)}")

                else:
                    print("  ❌ Does not support function calling")
                    results[model_id]['tools_tested'] = 'not_supported'

            except Exception as e:
                results[model_id] = {
                    'category': category,
                    'supports_function_calling': False,
                    'error': str(e),
                    'tools_tested': 'failed'
                }
                print(f"  ❌ Model test failed: {e}")

            elapsed = time.time() - start_time
            print(".2f")

        print()

    return results

def analyze_results(results):
    """Analyze the test results."""
    print("📈 ANALYSIS OF RESULTS")
    print("=" * 80)

    # Count by category
    category_stats = {}
    for model_id, data in results.items():
        cat = data['category']
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'with_tools': 0}
        category_stats[cat]['total'] += 1
        if data.get('supports_function_calling', False):
            category_stats[cat]['with_tools'] += 1

    print("📊 Models by category:")
    for cat, stats in category_stats.items():
        pct = (stats['with_tools'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {cat.upper()}: {stats['with_tools']}/{stats['total']} models support tools ({pct:.1f}%)")
    # Find best models
    print("\n🏆 BEST MODELS FOR TOOLS:")
    tool_supported_models = [
        (model_id, data) for model_id, data in results.items()
        if data.get('supports_function_calling', False)
    ]

    if tool_supported_models:
        # Sort by number of successful tool tests
        tool_supported_models.sort(
            key=lambda x: len([t for t in x[1].get('tools_tested', {}).values() if t == 'success']),
            reverse=True
        )

        for model_id, data in tool_supported_models[:5]:  # Top 5
            successful_tools = len([t for t in data.get('tools_tested', {}).values() if t == 'success'])
            total_tools = len(data.get('tools_tested', {}))
            print(f"  🏅 {model_id}: {successful_tools}/{total_tools} tools working")

    # Find problematic models
    print("\n⚠️  MODELS WITH ISSUES:")
    problematic = [
        (model_id, data) for model_id, data in results.items()
        if data.get('errors') or any('error' in str(v) for v in data.get('tools_tested', {}).values())
    ]

    for model_id, data in problematic[:5]:  # Show top 5 problematic
        error_count = len(data.get('errors', []))
        print(f"  ❌ {model_id}: {error_count} errors")

    return results

def suggest_new_tools(results):
    """Suggest new tools based on test results."""
    print("\n💡 SUGGESTIONS FOR NEW TOOLS")
    print("=" * 80)

    # Analyze what tools are missing or could be improved
    suggestions = [
        {
            'name': 'run_python',
            'description': 'Execute Python code safely',
            'reason': 'Useful for testing code snippets, calculations, data processing',
            'difficulty': 'Medium'
        },
        {
            'name': 'http_request',
            'description': 'Make HTTP requests to APIs',
            'reason': 'Complements web_search, allows API interactions',
            'difficulty': 'Easy'
        },
        {
            'name': 'json_processor',
            'description': 'Parse, validate, and manipulate JSON data',
            'reason': 'Common data format, useful for API responses and config files',
            'difficulty': 'Easy'
        },
        {
            'name': 'file_compressor',
            'description': 'Compress/decompress files (zip, tar, gzip)',
            'reason': 'Common file operations for backups and transfers',
            'difficulty': 'Medium'
        },
        {
            'name': 'git_operations',
            'description': 'Basic git commands (status, diff, log, commit)',
            'reason': 'Essential for development workflows',
            'difficulty': 'Medium'
        },
        {
            'name': 'database_query',
            'description': 'Execute SQL queries on databases',
            'reason': 'Useful for data analysis and database work',
            'difficulty': 'Hard'
        },
        {
            'name': 'image_processor',
            'description': 'Basic image operations (resize, convert format)',
            'reason': 'Common media processing tasks',
            'difficulty': 'Hard'
        }
    ]

    print("🔧 Proposed new tools:")
    for i, tool in enumerate(suggestions, 1):
        print(f"\n{i}. {tool['name']}")
        print(f"   📝 {tool['description']}")
        print(f"   💡 {tool['reason']}")
        print(f"   ⚡ Difficulty: {tool['difficulty']}")

    return suggestions

def save_results(results, filename="model_test_results.json"):
    """Save test results to file."""
    timestamp = datetime.now().isoformat()

    data = {
        'timestamp': timestamp,
        'total_models_tested': len(results),
        'results': results
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 Results saved to: {filename}")

def main():
    """Run comprehensive model testing."""
    start_time = time.time()

    results = test_all_models_with_tools()
    analyze_results(results)
    suggestions = suggest_new_tools(results)
    save_results(results)

    total_time = time.time() - start_time
    print(f"\n⏱️  Total testing time: {total_time:.2f} seconds")
    print("\n🎯 NEXT STEPS:")
    print("1. Review the results above")
    print("2. Decide which new tools to implement")
    print("3. Test the new tools with the best models")
    print("4. Update the CLI with improvements")

if __name__ == "__main__":
    main()