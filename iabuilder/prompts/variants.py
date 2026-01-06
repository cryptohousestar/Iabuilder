"""Prompt variants for different model families.

This module provides specialized prompts optimized for different model families,
taking into account their unique strengths and quirks when it comes to function calling.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import BasePromptTemplate, StrictnessLevel


class ModelFamily(Enum):
    """Model family identifiers."""

    LLAMA_70B = "llama-70b"  # Large LLaMA models (70B+)
    LLAMA_8B = "llama-8b"  # Small LLaMA models (8B-13B)
    CLAUDE = "claude"  # Anthropic Claude
    GPT4 = "gpt-4"  # OpenAI GPT-4 family
    GPT35 = "gpt-3.5"  # OpenAI GPT-3.5
    GEMINI = "gemini"  # Google Gemini
    QWEN = "qwen"  # Alibaba Qwen
    DEEPSEEK = "deepseek"  # DeepSeek
    MISTRAL = "mistral"  # Mistral/Mixtral
    COMMAND = "command"  # Cohere Command
    UNKNOWN = "unknown"  # Fallback for unknown models


def detect_model_family(model_name: str) -> ModelFamily:
    """Detect model family from model name.

    Args:
        model_name: Name or ID of the model

    Returns:
        Detected ModelFamily enum value
    """
    model_lower = model_name.lower()

    # Claude models
    if "claude" in model_lower:
        return ModelFamily.CLAUDE

    # GPT models
    if "gpt-4" in model_lower:
        return ModelFamily.GPT4
    if "gpt-3.5" in model_lower or "gpt-35" in model_lower:
        return ModelFamily.GPT35

    # Gemini models
    if "gemini" in model_lower or "gemma" in model_lower:
        return ModelFamily.GEMINI

    # Qwen models
    if "qwen" in model_lower:
        return ModelFamily.QWEN

    # DeepSeek models
    if "deepseek" in model_lower:
        return ModelFamily.DEEPSEEK

    # Mistral/Mixtral models
    if "mistral" in model_lower or "mixtral" in model_lower:
        return ModelFamily.MISTRAL

    # Cohere models
    if "command" in model_lower:
        return ModelFamily.COMMAND

    # LLaMA models - distinguish by size
    if "llama" in model_lower:
        # Extract parameter count if present
        size_match = re.search(r'(\d+)b', model_lower)
        if size_match:
            size = int(size_match.group(1))
            if size >= 70:
                return ModelFamily.LLAMA_70B
            else:
                return ModelFamily.LLAMA_8B
        # Default to 70B if size not specified (conservative choice)
        return ModelFamily.LLAMA_70B

    return ModelFamily.UNKNOWN


class PromptVariantManager:
    """Manages prompt variants for different model families.

    This class provides specialized prompts and instructions optimized
    for different model families' unique characteristics.
    """

    def __init__(self, model_name: str):
        """Initialize the variant manager.

        Args:
            model_name: Name/ID of the model to generate prompts for
        """
        self.model_name = model_name
        self.family = detect_model_family(model_name)

    def get_function_calling_instructions(self) -> str:
        """Get function calling instructions specific to this model family.

        Returns:
            Specialized function calling instructions
        """
        instructions = {
            ModelFamily.LLAMA_70B: self._get_llama_70b_instructions(),
            ModelFamily.LLAMA_8B: self._get_llama_8b_instructions(),
            ModelFamily.CLAUDE: self._get_claude_instructions(),
            ModelFamily.GPT4: self._get_gpt4_instructions(),
            ModelFamily.GPT35: self._get_gpt35_instructions(),
            ModelFamily.GEMINI: self._get_gemini_instructions(),
            ModelFamily.QWEN: self._get_qwen_instructions(),
            ModelFamily.DEEPSEEK: self._get_deepseek_instructions(),
            ModelFamily.MISTRAL: self._get_mistral_instructions(),
            ModelFamily.COMMAND: self._get_command_instructions(),
            ModelFamily.UNKNOWN: self._get_generic_instructions(),
        }

        return instructions[self.family]

    def get_tool_usage_examples(self, tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """Get tool usage examples appropriate for this model family.

        Args:
            tools: Optional list of available tools to use in examples

        Returns:
            Example usage patterns
        """
        # For simpler models, provide more explicit examples
        if self.family in [ModelFamily.LLAMA_8B, ModelFamily.GPT35]:
            return self._get_detailed_examples(tools)
        # For advanced models, minimal examples suffice
        elif self.family in [ModelFamily.CLAUDE, ModelFamily.GPT4]:
            return self._get_minimal_examples(tools)
        # For code-focused models, use code-centric examples
        elif self.family in [ModelFamily.DEEPSEEK, ModelFamily.QWEN]:
            return self._get_code_focused_examples(tools)
        else:
            return self._get_standard_examples(tools)

    def get_recommended_strictness(self) -> StrictnessLevel:
        """Get recommended strictness level for this model family.

        Returns:
            Recommended StrictnessLevel
        """
        # Small models need very detailed instructions
        if self.family == ModelFamily.LLAMA_8B:
            return StrictnessLevel.MAXIMUM

        # Mid-size or code models benefit from detailed instructions
        elif self.family in [ModelFamily.LLAMA_70B, ModelFamily.DEEPSEEK, ModelFamily.QWEN, ModelFamily.GPT35]:
            return StrictnessLevel.DETAILED

        # Advanced models work well with standard instructions
        elif self.family in [ModelFamily.CLAUDE, ModelFamily.GPT4, ModelFamily.GEMINI]:
            return StrictnessLevel.STANDARD

        # Unknown models get detailed by default (safe choice)
        else:
            return StrictnessLevel.DETAILED

    # Model family specific instructions

    def _get_llama_70b_instructions(self) -> str:
        """Instructions optimized for LLaMA 70B+ models."""
        return """## Function Calling for LLaMA 70B

You are using a LLaMA 70B model. When calling functions:

1. THINK FIRST: Before calling a function, briefly explain your reasoning
2. BE EXPLICIT: Clearly state which function you're calling and why
3. CHECK PARAMETERS: Verify all required parameters are included
4. USE EXAMPLES: Refer to the examples provided when uncertain

Function Call Format:
- Identify the appropriate function
- Gather all required parameters
- Make the call with proper JSON formatting
- Wait for results before responding

Common Mistakes to Avoid:
- Don't invent function names - use only provided functions
- Don't skip required parameters
- Don't call multiple functions without waiting for results
- Don't hallucinate function outputs"""

    def _get_llama_8b_instructions(self) -> str:
        """Instructions optimized for smaller LLaMA models (8B-13B)."""
        return """## IMPORTANT: Function Calling Instructions for LLaMA 8B

YOU MUST FOLLOW THESE RULES EXACTLY:

Rule 1: ONLY use functions that are listed in the "Available Tools" section
Rule 2: ALWAYS include ALL required parameters
Rule 3: NEVER make up function names or parameters
Rule 4: CALL ONE FUNCTION AT A TIME and wait for results
Rule 5: If you're not sure, ASK the user for clarification

STEP-BY-STEP PROCESS:

Step 1: Read the user's question carefully
Step 2: Look at the available functions
Step 3: Pick the ONE function that best matches the need
Step 4: Check what parameters it needs
Step 5: Make sure you have all required information
Step 6: Call the function with correct parameters
Step 7: Wait for the result
Step 8: Give the user a clear answer based on the result

CRITICAL REMINDERS:
- Do NOT invent functions
- Do NOT skip parameters
- Do NOT call functions that aren't listed
- Do NOT make up results - wait for actual output

If you cannot find a suitable function, tell the user you don't have the right tool for that task."""

    def _get_claude_instructions(self) -> str:
        """Instructions optimized for Claude models."""
        return """## Function Calling with Claude

You have access to various tools. Claude models excel at thoughtful, step-by-step reasoning:

Approach:
1. Understand the user's intent deeply
2. Consider which tool(s) would be most appropriate
3. Think through the parameters needed
4. Execute the tool call
5. Interpret results in context of the original question
6. Provide a comprehensive, well-reasoned response

Your strengths:
- Deep contextual understanding
- Thoughtful analysis of tool outputs
- Clear explanation of reasoning
- Handling complex, multi-step tasks

Best practices:
- Take time to reason through complex requests
- Combine multiple tool results when needed
- Explain your thought process when helpful
- Provide nuanced interpretations of data"""

    def _get_gpt4_instructions(self) -> str:
        """Instructions optimized for GPT-4 models."""
        return """## Function Calling with GPT-4

Available tools can be called as needed. GPT-4 best practices:

Efficiency:
- Identify the optimal tool for each task
- Minimize unnecessary tool calls
- Chain tool calls intelligently for complex tasks
- Parallelize independent operations when possible

Quality:
- Validate parameters before calling
- Handle errors gracefully
- Synthesize results concisely
- Provide actionable insights

Your approach should be:
- Direct and efficient
- Accurate and reliable
- Clear and well-structured
- Context-aware"""

    def _get_gpt35_instructions(self) -> str:
        """Instructions optimized for GPT-3.5 models."""
        return """## Function Calling with GPT-3.5

IMPORTANT GUIDELINES for reliable function calling:

1. IDENTIFY: Determine which function matches the user's need
2. PREPARE: Gather all required parameters
3. VALIDATE: Double-check parameter names and types
4. EXECUTE: Call the function with proper formatting
5. RESPOND: Use the results to answer the user

Key Points:
- Use ONLY the functions listed in "Available Tools"
- Include ALL required parameters (check the parameter list)
- Call ONE function at a time
- Wait for results before making additional calls
- If unsure about parameters, ask the user

Error Prevention:
- Don't invent function names
- Don't skip required parameters
- Don't assume parameter values
- Don't call functions that don't exist"""

    def _get_gemini_instructions(self) -> str:
        """Instructions optimized for Gemini models."""
        return """## Function Calling with Gemini

Function calling guidelines for Gemini:

Direct Approach:
1. Parse user request clearly
2. Select appropriate function
3. Provide required parameters
4. Execute and analyze results
5. Deliver concise response

Principles:
- Be direct and clear in your function usage
- Focus on accuracy over verbosity
- Use structured output formats when appropriate
- Handle multimodal inputs effectively (if applicable)

Function Call Process:
- Identify: Which function solves this?
- Validate: Do I have the needed parameters?
- Execute: Call with correct format
- Respond: Present results clearly"""

    def _get_qwen_instructions(self) -> str:
        """Instructions optimized for Qwen models."""
        return """## Function Calling with Qwen

Qwen function calling protocol:

Minimal, Precise Approach:
1. Identify required function
2. Extract parameters
3. Execute call
4. Return results

Guidelines:
- Be precise and minimal in function calls
- Focus on technical accuracy
- Use structured formats
- Avoid unnecessary elaboration

Format:
```
Action: [function_name]
Parameters: {param: value, ...}
Result: [wait for output]
Response: [interpret and present]
```

Keep function usage straightforward and technically sound."""

    def _get_deepseek_instructions(self) -> str:
        """Instructions optimized for DeepSeek models."""
        return """## Function Calling with DeepSeek

DeepSeek function calling approach (optimized for code and technical tasks):

Structured Process:
```
1. ANALYZE: Understand the request
2. SELECT: Choose appropriate function(s)
3. PREPARE: Structure parameters correctly
4. EXECUTE: Make the function call
5. VERIFY: Check outputs are valid
6. RESPOND: Format response clearly
```

Best Practices:
- Use precise, well-structured parameters
- Pay attention to data types and formats
- Handle edge cases explicitly
- Validate inputs and outputs
- Structure responses logically

For code-related tasks:
- Prefer programmatic approaches
- Use functions systematically
- Chain operations logically
- Return structured data when possible

Error Handling:
- Catch and report errors clearly
- Suggest corrections when functions fail
- Provide alternative approaches"""

    def _get_mistral_instructions(self) -> str:
        """Instructions optimized for Mistral/Mixtral models."""
        return """## Function Calling with Mistral

Mistral models function calling guide:

Approach:
1. Understand user intent
2. Select optimal function(s)
3. Prepare parameters carefully
4. Execute function calls
5. Synthesize results

Function Usage:
- Choose functions based on explicit user needs
- Ensure parameter completeness
- Handle multi-step tasks efficiently
- Provide clear, structured responses

Quality Standards:
- Accuracy in parameter extraction
- Efficient tool selection
- Clear result interpretation
- Helpful error messages

Remember: Mistral models are efficient and capable - use tools confidently but precisely."""

    def _get_command_instructions(self) -> str:
        """Instructions optimized for Cohere Command models."""
        return """## Function Calling with Cohere Command

Command model function usage:

Process:
1. Parse user query
2. Determine if a function can help
3. Select the most appropriate function
4. Gather required parameters (ask user if needed)
5. Execute the function call
6. Integrate results into response

Command Model Strengths:
- Strong retrieval and search capabilities
- Excellent at parameter extraction from text
- Good at multi-step reasoning
- Effective citation and source attribution

Best Practices:
- Use functions to augment knowledge, not replace reasoning
- Cite function results when presenting information
- Chain functions for complex queries
- Validate function outputs before presenting
- Provide context around function results"""

    def _get_generic_instructions(self) -> str:
        """Generic instructions for unknown models."""
        return """## Function Calling Instructions

General guidelines for using available functions:

1. SELECTION: Choose the function that best matches the user's need
2. PARAMETERS: Ensure all required parameters are provided
3. EXECUTION: Call the function with proper formatting
4. INTERPRETATION: Analyze the results
5. RESPONSE: Present findings clearly to the user

Important Rules:
- Only use functions listed in "Available Tools"
- Include all required parameters
- Use correct parameter types and formats
- Wait for function results before responding
- Handle errors gracefully

Process:
1. Read the user's request
2. Review available functions
3. Select appropriate function(s)
4. Prepare parameters
5. Execute function call(s)
6. Synthesize results
7. Provide helpful response"""

    # Example generation methods

    def _get_detailed_examples(self, tools: Optional[List[Dict[str, Any]]]) -> str:
        """Get detailed examples for models that need extra guidance."""
        return """## Function Calling Examples

Example 1: Simple function call
User: "What's the weather in Paris?"
Thinking: I need to use the weather function with location="Paris"
Action: Call weather_tool(location="Paris")
Result: [Wait for weather data]
Response: "In Paris, it's currently 15°C and partly cloudy..."

Example 2: Function with multiple parameters
User: "Search for Python tutorials from the last week"
Thinking: I need search function with query and date filter
Action: Call search_tool(query="Python tutorials", date_range="last_week")
Result: [Wait for search results]
Response: "I found several recent Python tutorials: [list results]"

Example 3: When function isn't needed
User: "What is Python?"
Thinking: I can answer this from general knowledge, no function needed
Response: "Python is a high-level programming language..."

Example 4: Asking for clarification
User: "Get me the data"
Thinking: "data" is too vague - need to ask what data they want
Response: "I'd be happy to help! What specific data are you looking for?"

REMEMBER:
- Think before you act
- Use functions only when needed
- Include all required parameters
- Wait for results before responding"""

    def _get_minimal_examples(self, tools: Optional[List[Dict[str, Any]]]) -> str:
        """Get minimal examples for advanced models."""
        return """## Example Function Usage

Simple query:
User: "Current time in Tokyo"
→ Call time_tool(location="Tokyo", timezone="Asia/Tokyo")
→ Present result

Complex query:
User: "Compare weather in Tokyo and London"
→ Call weather_tool(location="Tokyo")
→ Call weather_tool(location="London")
→ Synthesize and compare results"""

    def _get_code_focused_examples(self, tools: Optional[List[Dict[str, Any]]]) -> str:
        """Get code-centric examples for technical models."""
        return """## Function Usage Examples (Code-Focused)

Example: API query
```
Input: "Fetch user data for ID 12345"
Process:
  1. function: get_user_data
  2. params: {"user_id": 12345}
  3. validate: user_id is integer ✓
  4. execute: call function
  5. output: return formatted user object
```

Example: Multi-step operation
```
Input: "Search and summarize latest AI news"
Process:
  1. search_tool(query="AI news", limit=5)
  2. for each result: fetch_content(url)
  3. summarize_text(content=combined_text)
  4. return structured summary
```

Pattern: Always validate → execute → verify → respond"""

    def _get_standard_examples(self, tools: Optional[List[Dict[str, Any]]]) -> str:
        """Get standard examples for most models."""
        return """## Function Calling Examples

Example 1: Direct function call
User: "What's the capital of France?"
→ If knowledge_tool available: Call knowledge_tool(query="capital of France")
→ Otherwise: Answer directly: "Paris"

Example 2: Multi-parameter function
User: "Search for restaurants in Seattle with good ratings"
→ Call search_tool(query="restaurants", location="Seattle", filter="high_rating")
→ Present top results

Example 3: Chained functions
User: "Find and summarize the latest tech news"
→ Step 1: search_tool(query="tech news", date="today")
→ Step 2: fetch_content(url=top_result_url)
→ Step 3: summarize(text=content)
→ Present summary with source"""


def create_optimized_prompt(
    model_name: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    context: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    override_strictness: Optional[StrictnessLevel] = None
) -> str:
    """Create an optimized prompt for a specific model.

    Args:
        model_name: Name/ID of the model
        tools: Available tools/functions
        context: Additional context
        custom_instructions: Custom instructions to append
        override_strictness: Override recommended strictness level

    Returns:
        Complete optimized system prompt
    """
    manager = PromptVariantManager(model_name)

    # Get recommended strictness or use override
    strictness = override_strictness or manager.get_recommended_strictness()

    # Create base prompt
    base_template = BasePromptTemplate(strictness, custom_instructions)
    base_prompt = base_template.build_system_prompt(tools, context)

    # Add model-specific function calling instructions
    function_instructions = manager.get_function_calling_instructions()

    # Add examples if tools are provided
    examples = ""
    if tools:
        examples = manager.get_tool_usage_examples(tools)

    # Combine all sections
    sections = [base_prompt, function_instructions]
    if examples:
        sections.append(examples)

    return "\n\n".join(sections)
