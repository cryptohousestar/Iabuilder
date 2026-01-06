

import sys
import os
from iabuilder.main import IABuilderApp
from iabuilder.tools import get_tool_registry

def test_consolidated_architecture():
    print("🧪 TESTING: Llama 8B Optimization Architecture")
    print("=" * 50)
    
    try:
        # Initialize App
        app = IABuilderApp()
        
        # Check Tool Registry
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        print(f"📊 Tools Registered: {len(tools)}")
        print(f"📋 List: {', '.join(tools)}")
        
        # Verify Key Tools exist
        required = ['file_manager', 'git_manager', 'system_manager']
        missing = [t for t in required if t not in tools]
        
        if missing:
            print(f"❌ FAILED: Missing consolidated tools: {missing}")
            sys.exit(1)
        else:
            print("✅ SUCCESS: All consolidated tools present")
            
        # Test Execution of a Consolidated Tool
        print("\n🔄 Testing 'file_manager' (read action)...")
        file_tool = registry.get('file_manager')
        result = file_tool.execute(action="read", file_path="requirements.txt")
        
        if "groq" in result.lower() or "requests" in result.lower():
             print("✅ SUCCESS: Tool execution worked perfectly")
             print(f"   (Read {len(result)} chars from requirements.txt)")
        else:
             print(f"⚠️ WARNING: Tool output unexpected: {result[:100]}...")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_consolidated_architecture()
