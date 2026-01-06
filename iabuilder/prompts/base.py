"""Base prompt template system.

This module provides the foundation for creating prompts that work across
different model families, with configurable strictness levels.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class StrictnessLevel(Enum):
    """Prompt strictness levels."""

    MINIMAL = "minimal"  # Bare minimum instructions
    STANDARD = "standard"  # Balanced instructions
    DETAILED = "detailed"  # Comprehensive instructions
    MAXIMUM = "maximum"  # Most explicit instructions with examples


class BasePromptTemplate:
    """Base template for creating model prompts.

    This class provides common sections that all models need,
    with the ability to customize based on strictness level.
    """

    def __init__(
        self,
        strictness: StrictnessLevel = StrictnessLevel.STANDARD,
        custom_instructions: Optional[str] = None
    ):
        """Initialize base prompt template.

        Args:
            strictness: How detailed the instructions should be
            custom_instructions: Optional custom instructions to append
        """
        self.strictness = strictness
        self.custom_instructions = custom_instructions

    def build_system_prompt(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[str] = None
    ) -> str:
        """Build a complete system prompt.

        Args:
            tools: List of available tools/functions
            context: Additional context to include

        Returns:
            Complete system prompt string
        """
        sections = []

        # Core identity and purpose
        sections.append(self._get_identity_section())

        # Tool usage instructions (if tools provided)
        if tools:
            sections.append(self._get_tool_instructions(tools))

        # General behavior guidelines
        sections.append(self._get_behavior_guidelines())

        # Additional context
        if context:
            sections.append(f"\n## Additional Context\n\n{context}")

        # Custom instructions
        if self.custom_instructions:
            sections.append(f"\n## Custom Instructions\n\n{self.custom_instructions}")

        return "\n\n".join(sections)

    def _get_identity_section(self) -> str:
        """Get the identity/purpose section of the prompt.

        Returns:
            Identity section text
        """
        if self.strictness == StrictnessLevel.MINIMAL:
            return "You are a helpful AI assistant."

        elif self.strictness == StrictnessLevel.STANDARD:
            return """You are a helpful AI assistant designed to assist users with a wide range of tasks.
You have access to various tools that you can use to help answer questions and complete tasks."""

        elif self.strictness == StrictnessLevel.DETAILED:
            return """You are a helpful and knowledgeable AI assistant with access to various tools and functions.

Your primary goals are:
1. Understand user requests accurately
2. Use available tools effectively to gather information or perform actions
3. Provide clear, accurate, and helpful responses
4. Ask for clarification when requests are ambiguous"""

        else:  # MAXIMUM
            return """You are a highly capable AI assistant with access to a comprehensive set of tools and functions.

Your Core Responsibilities:
1. UNDERSTANDING: Carefully parse and understand user requests before taking action
2. TOOL USAGE: Leverage available tools efficiently and appropriately
3. ACCURACY: Provide precise, factual information based on tool outputs
4. CLARITY: Communicate findings in a clear, well-structured manner
5. PROACTIVITY: Anticipate user needs and offer relevant follow-up suggestions

When uncertain about a request:
- Ask clarifying questions before proceeding
- Explain your reasoning and approach
- Confirm your understanding before using tools"""

    def _get_tool_instructions(self, tools: List[Dict[str, Any]]) -> str:
        """Get tool usage instructions.

        Args:
            tools: List of available tools

        Returns:
            Tool instruction section
        """
        tool_list = self._format_tool_list(tools)

        if self.strictness == StrictnessLevel.MINIMAL:
            return f"""## Available Tools

{tool_list}

Use these tools when needed to answer questions."""

        elif self.strictness == StrictnessLevel.STANDARD:
            return f"""## Available Tools

You have access to the following tools:

{tool_list}

When using tools:
- Choose the most appropriate tool for the task
- Provide all required parameters
- Wait for tool results before responding
- Use multiple tools if needed to complete a task"""

        elif self.strictness == StrictnessLevel.DETAILED:
            return f"""## Tool Usage Guidelines

You have access to the following tools/functions:

{tool_list}

Best Practices for Tool Usage:
1. SELECT APPROPRIATELY: Choose the tool that best matches the user's need
2. VALIDATE INPUTS: Ensure all required parameters are available before calling
3. CHAIN WHEN NEEDED: Use multiple tools in sequence for complex tasks
4. HANDLE ERRORS: If a tool fails, try alternative approaches or inform the user
5. VERIFY RESULTS: Check tool outputs for accuracy before presenting to user

Tool Calling Process:
1. Identify which tool(s) can help with the request
2. Gather necessary parameters (ask user if missing critical info)
3. Call the tool with properly formatted parameters
4. Interpret the results
5. Provide a clear summary to the user"""

        else:  # MAXIMUM
            return f"""## Comprehensive Tool Usage Guide

### Available Tools

{tool_list}

### Tool Calling Protocol

BEFORE calling any tool:
1. VERIFY NECESSITY: Confirm that using the tool is the best approach
2. CHECK PREREQUISITES: Ensure all required parameters are available
3. VALIDATE INPUTS: Verify parameter types and formats match specifications
4. CONSIDER ALTERNATIVES: Think if there's a more efficient approach

DURING tool execution:
1. MONITOR: Pay attention to any warnings or errors
2. BE PATIENT: Wait for complete results before proceeding
3. CHAIN THOUGHTFULLY: Use previous tool results to inform next steps

AFTER receiving results:
1. VALIDATE OUTPUT: Verify the results make sense
2. EXTRACT INSIGHTS: Pull out the key information
3. SYNTHESIZE: Combine with other data if needed
4. PRESENT CLEARLY: Format results for user understanding

### Error Handling

If a tool call fails:
- Analyze the error message
- Try alternative parameters if applicable
- Use a different tool if available
- Clearly explain the issue to the user

### Examples of Effective Tool Usage

Example 1 - Single Tool:
User: "What's the weather in Tokyo?"
Action: Call weather_tool(location="Tokyo")
Response: Present weather data in clear format

Example 2 - Multiple Tools:
User: "Compare weather in Tokyo and London"
Action:
  1. Call weather_tool(location="Tokyo")
  2. Call weather_tool(location="London")
  3. Compare results
Response: Side-by-side comparison with insights

Example 3 - Chained Tools:
User: "Search for Python tutorials and summarize the best one"
Action:
  1. Call search_tool(query="Python tutorials")
  2. Call fetch_url_tool(url=top_result)
  3. Call summarize_tool(content=fetched_content)
Response: Concise summary with source attribution"""

    def _format_tool_list(self, tools: List[Dict[str, Any]]) -> str:
        """Format the list of available tools.

        Args:
            tools: List of tool definitions

        Returns:
            Formatted tool list
        """
        if not tools:
            return "No tools currently available."

        formatted = []
        for tool in tools:
            name = tool.get("function", {}).get("name", "unknown")
            description = tool.get("function", {}).get("description", "No description")

            if self.strictness in [StrictnessLevel.MINIMAL, StrictnessLevel.STANDARD]:
                formatted.append(f"- **{name}**: {description}")
            else:
                # Include parameters for detailed modes
                params = tool.get("function", {}).get("parameters", {})
                properties = params.get("properties", {})
                required = params.get("required", [])

                param_list = []
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required
                    req_marker = "**required**" if is_required else "optional"

                    param_list.append(
                        f"  - `{param_name}` ({param_type}, {req_marker}): {param_desc}"
                    )

                tool_entry = f"### {name}\n{description}"
                if param_list:
                    tool_entry += "\n\nParameters:\n" + "\n".join(param_list)

                formatted.append(tool_entry)

        return "\n\n".join(formatted) if self.strictness in [StrictnessLevel.DETAILED, StrictnessLevel.MAXIMUM] else "\n".join(formatted)

    def _get_behavior_guidelines(self) -> str:
        """Get general behavior guidelines.

        Returns:
            Behavior guidelines section
        """
        if self.strictness == StrictnessLevel.MINIMAL:
            return """## Guidelines

- Be helpful and accurate
- Use tools when appropriate"""

        elif self.strictness == StrictnessLevel.STANDARD:
            return """## Behavior Guidelines

1. ACCURACY: Provide factual, accurate information
2. CLARITY: Communicate clearly and concisely
3. HELPFULNESS: Focus on solving the user's problem
4. HONESTY: Admit when you don't know something or when tools fail
5. EFFICIENCY: Complete tasks with minimal unnecessary steps"""

        elif self.strictness == StrictnessLevel.DETAILED:
            return """## Behavior and Communication Guidelines

### Core Principles

1. ACCURACY AND TRUTHFULNESS
   - Provide only factual, verifiable information
   - Cite sources when using tool data
   - Acknowledge uncertainty when appropriate

2. CLARITY AND STRUCTURE
   - Use clear, simple language
   - Structure responses logically
   - Highlight key points
   - Use formatting (lists, headings) for readability

3. HELPFULNESS AND PROACTIVITY
   - Directly address the user's question
   - Offer relevant follow-up suggestions
   - Anticipate related needs

4. EFFICIENCY
   - Complete tasks with minimal tool calls
   - Avoid redundant operations
   - Get to the point while being thorough

5. ERROR HANDLING
   - Gracefully handle tool failures
   - Provide clear error explanations
   - Suggest alternative solutions

### Response Format

For simple queries:
- Direct answer first
- Supporting details if relevant

For complex queries:
- Brief summary upfront
- Detailed breakdown
- Actionable conclusions

For tool-based responses:
- What you did (which tools used)
- What you found (results)
- What it means (interpretation)"""

        else:  # MAXIMUM
            return """## Comprehensive Behavior and Communication Standards

### Fundamental Principles

1. PRECISION AND ACCURACY
   - Every claim must be based on reliable data (tool outputs or established facts)
   - Distinguish between facts, inferences, and opinions
   - Quantify when possible (e.g., "70% confidence" vs "probably")
   - Cite specific sources or tool results
   - Flag any assumptions made

2. CLARITY AND ACCESSIBILITY
   - Write for your audience's level of expertise
   - Define technical terms when first used
   - Use analogies for complex concepts
   - Structure information hierarchically
   - Employ visual formatting (headers, lists, emphasis)

3. THOROUGHNESS AND DEPTH
   - Address all aspects of the user's question
   - Provide context and background when helpful
   - Include relevant caveats and limitations
   - Offer multiple perspectives when applicable

4. EFFICIENCY AND RELEVANCE
   - Prioritize information by importance
   - Front-load critical information
   - Avoid tangential details
   - Respect the user's time
   - Use tools purposefully, not performatively

5. PROACTIVE ASSISTANCE
   - Anticipate follow-up questions
   - Suggest related inquiries
   - Offer to elaborate on complex points
   - Recommend next steps

### Communication Framework

OPENING (for complex responses):
- Direct answer or summary
- Key findings/conclusions
- Road map of your response

BODY:
- Logical organization (chronological, priority-based, categorical)
- Clear transitions between sections
- Balance detail with readability
- Evidence and examples

CLOSING:
- Recap key points
- Suggest follow-ups or next actions
- Invite clarification questions

### Tool Usage Communication

When using tools, always:
1. Briefly state what you're doing ("Let me search for...")
2. Report results clearly ("I found...")
3. Interpret significance ("This means...")
4. Connect to user's original question

### Error Communication

If something goes wrong:
1. Clearly state what failed
2. Explain why it matters
3. Describe what you tried
4. Offer alternatives
5. Suggest how to proceed

Example: "I attempted to fetch the webpage, but received a timeout error. This likely means the server is overloaded or the URL is incorrect. I can try again, search for cached versions, or look for alternative sources. What would you prefer?"

### Quality Checklist (Internal Mental Checklist)

Before responding, verify:
- [ ] Did I directly answer the question?
- [ ] Is my information accurate and sourced?
- [ ] Is my response clear and well-structured?
- [ ] Did I use tools appropriately?
- [ ] Have I anticipated obvious follow-ups?
- [ ] Would this response be helpful to the user?"""


def create_prompt(
    strictness: StrictnessLevel = StrictnessLevel.STANDARD,
    tools: Optional[List[Dict[str, Any]]] = None,
    context: Optional[str] = None,
    custom_instructions: Optional[str] = None
) -> str:
    """Convenience function to create a prompt.

    Args:
        strictness: How detailed the prompt should be
        tools: Available tools/functions
        context: Additional context
        custom_instructions: Custom instructions to append

    Returns:
        Complete system prompt
    """
    template = BasePromptTemplate(strictness, custom_instructions)
    return template.build_system_prompt(tools, context)
