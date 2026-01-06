# IABuilder

**Intelligent Architecture Builder** - A universal, multi-provider AI development tool with function calling capabilities.

> Like Claude Code, but works with **ANY LLM provider** - Groq, OpenAI, Anthropic, Google, OpenRouter, Mistral, Together, DeepSeek, Cohere, and more!

## 🌟 Key Features

- 🔌 **Multi-Provider Support** - Switch between 9+ LLM providers seamlessly
- 🤖 **Universal Model Access** - Use models from any provider in one tool
- 🔧 **Function Calling** - Atomic tools like Claude CLI (read, write, edit, bash, search)
- 🎯 **Intelligent Prompts** - Optimized prompts for each model family
- 📁 **Project-Aware** - Automatic project detection and context
- 🗜️ **Context Compression** - Unlimited conversation length (like Claude Code)
- 🎨 **Rich Terminal UI** - Beautiful markdown rendering
- 🚀 **Works Anywhere** - Use from any project directory (like Cursor Agent)
- 🌍 **Cross-Platform** - Runs on Linux, macOS, and Windows

## 🔌 Supported Providers

IABuilder works with **any LLM provider**:

| Provider | Models | Auto-Detection | Function Calling |
|----------|--------|----------------|------------------|
| **Groq** | LLaMA 3.3 70B, 3.1 8B, Mixtral | ✅ | ✅ |
| **OpenAI** | GPT-4, GPT-3.5 Turbo | ✅ | ✅ |
| **Anthropic** | Claude Opus, Sonnet, Haiku | ❌ (Manual) | ✅ |
| **Google** | Gemini Pro, Ultra | ✅ | ✅ |
| **OpenRouter** | 100+ models from all providers | ✅ | ✅ |
| **Mistral** | Mistral Large, Codestral, Mixtral | ✅ | ✅ |
| **Together** | LLaMA, Qwen, DeepSeek, 100+ OSS | ✅ | ✅ |
| **DeepSeek** | DeepSeek V3, Coder, Reasoner | ✅ | ✅ |
| **Cohere** | Command R+, Command R | ✅ | ✅ |
| **Custom** | Any OpenAI-compatible API | ✅ | ✅ |

## 🚀 Quick Start

### Supported Platforms
- ✅ **Linux** (Ubuntu, Debian, Fedora, etc.) - *Fully tested*
- ✅ **macOS** (10.15+) - *Should work identically to Linux*
- ✅ **Windows** (10/11 with PowerShell) - *Compatible, may need testing*

### Downloads
Get the latest release from [GitHub Releases](https://github.com/cryptohousestar/Iabuilder/releases):

| Platform | Download | Installer |
|----------|----------|-----------|
| **Linux** | [TAR.GZ](https://github.com/cryptohousestar/Iabuilder/releases/latest/download/iabuilder-linux.tar.gz) | [Shell Script](https://github.com/cryptohousestar/Iabuilder/releases/latest/download/install_iabuilder_linux.sh) |
| **macOS** | [TAR.GZ](https://github.com/cryptohousestar/Iabuilder/releases/latest/download/iabuilder-macos.tar.gz) | [Shell Script](https://github.com/cryptohousestar/Iabuilder/releases/latest/download/install_iabuilder_macos.sh) |
| **Windows** | [ZIP](https://github.com/cryptohousestar/Iabuilder/releases/latest/download/iabuilder-windows.zip) | [PowerShell](https://github.com/cryptohousestar/Iabuilder/releases/latest/download/install_iabuilder_windows.ps1) |

### 1. Installation

#### Linux
```bash
# Clone repository
git clone <repository-url>
cd iabuilder

# Install using the automated script
./install_iabuilder.sh

# Or manual installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

#### macOS
```bash
# Clone repository
git clone <repository-url>
cd iabuilder

# Install using the macOS script
./install_iabuilder_macos.sh

# Or manual installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

#### Windows (PowerShell as Administrator)
```powershell
# Clone repository
git clone <repository-url>
cd iabuilder

# Install using the Windows script
.\install_iabuilder_windows.ps1

# Or manual installation
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Your First Provider

#### Linux/macOS
```bash
# Navigate to any project
cd ~/your-project

# Run IABuilder
iabuilder

# Configure a provider (interactive wizard)
/configure-api groq

# Or other providers
/configure-api openai
/configure-api anthropic
/configure-api google
```

#### Windows
```cmd
REM Navigate to any project
cd C:\your-project

REM Run IABuilder
iabuilder

REM Configure a provider (interactive wizard)
/configure-api groq

REM Or other providers
/configure-api openai
/configure-api anthropic
/configure-api google
```

### 3. How It Works on Each Platform

After installation, **IABuilder works identically on all platforms**. The AI automatically detects your current working directory and has access to all your project files.

#### Linux/macOS
```bash
# Navigate to your project
cd ~/my-project

# Run IABuilder - it automatically knows you're in ~/my-project
iabuilder

# The AI can now read/write files in ~/my-project
> List all Python files in this directory
> Create a new file called utils.py
> Run tests and fix any errors
```

#### Windows
```cmd
REM Navigate to your project
cd C:\my-project

REM Run IABuilder - it automatically knows you're in C:\my-project
iabuilder

REM The AI can now read/write files in C:\my-project
> List all Python files in this directory
> Create a new file called utils.py
> Run tests and fix any errors
```

**Key Points:**
- ✅ **Same commands** work on all platforms
- ✅ **Same AI capabilities** regardless of OS
- ✅ **Automatic project detection** - no need to specify paths
- ✅ **Cross-platform file operations** work seamlessly

### 4. Start Building

```bash
# List available models
/models

# Switch to a specific model
/model llama-3.3-70b-versatile

# Chat with AI - it knows your project context!
> Read the main.py file and explain what it does
> Create a new feature in utils.py
> Run the tests and fix any errors
```

## 📚 Usage Guide

### Basic Commands

```bash
# Get help
/help

# Chat
> Your message here

# Clear conversation
/clear

# Save conversation
/save my-session.md
```

### Provider Management

```bash
# Configure preset providers (Groq, OpenAI, Anthropic, Google, OpenRouter)
/configure-api [provider]

# Add custom provider
/add-provider

# View all configured providers
/status

# Remove a provider
/remove-api [name]
```

### Model Management

```bash
# List all available models
/models

# List models from specific provider
/models groq
/models openai

# Switch to a model
/model llama-3.3-70b-versatile
/model gpt-4
/model claude-opus-4

# Refresh model list from APIs
/refresh

# Refresh specific provider
/refresh groq

# Search for models
/search-models coding
/search-models fast

# Manually add a model (for providers without /models API)
/add-model
```

### Working with Multiple Providers

IABuilder lets you configure **multiple providers simultaneously** and switch between them:

```bash
# Configure multiple providers
/configure-api groq
/configure-api openai
/configure-api anthropic

# See all providers
/status

# List all models from all providers
/models

# Switch between providers by selecting their models
/model llama-3.3-70b-versatile    # Uses Groq
/model gpt-4                       # Uses OpenAI
/model claude-opus-4               # Uses Anthropic

# Your conversation context is preserved when switching!
```

## 🛠️ Available Tools

IABuilder provides **atomic, specialized tools** (like Claude CLI):

### File Operations
- `read_file` - Read file contents
- `write_file` - Create/overwrite files
- `edit_file` - Search and replace in files

### System Operations
- `execute_bash` - Run shell commands
- `run_python` - Execute Python code

### Search & Discovery
- `grep_search` - Search text in files (ripgrep)
- `glob_search` - Find files by pattern
- `web_search` - Search the internet

### Git Tools (auto-detected)
- `git_status` - Check repository status
- `git_commit` - Create commits
- `git_branch` - Manage branches
- `git_log` - View history

### Database Tools (auto-detected)
- `database_connector` - Connect to databases
- `query_executor` - Run SQL queries
- `database_schema` - Inspect schema

### Package Management (auto-detected)
- `package_installer` - Install dependencies
- `dependency_analyzer` - Analyze package tree
- `virtual_environment` - Manage venvs

## 🎯 Model Family Optimization

IABuilder automatically optimizes prompts for each model family:

| Family | Models | Optimization |
|--------|--------|-------------|
| **LLaMA 70B** | llama-3.3-70b, llama-3.1-70b | Detailed prompts, complex reasoning |
| **LLaMA 8B** | llama-3.1-8b, llama-3.2-8b | Concise prompts, direct instructions |
| **Claude** | claude-opus, claude-sonnet | Anthropic-optimized format |
| **GPT-4** | gpt-4, gpt-4-turbo | OpenAI best practices |
| **GPT-3.5** | gpt-3.5-turbo | Simplified, efficient prompts |
| **Gemini** | gemini-pro, gemini-ultra | Google-specific format |
| **Qwen** | qwen-72b, qwen-14b | Multilingual optimization |
| **DeepSeek** | deepseek-v3, deepseek-coder | Code-focused prompts |
| **Mistral** | mistral-large, mixtral | European model optimization |
| **Command** | command-r+, command-r | Cohere RAG optimization |

## 📦 Project Structure

```
iabuilder/
├── iabuilder/
│   ├── main.py                    # Main application
│   ├── cli.py                     # Interactive CLI
│   ├── client.py                  # Groq API client (legacy)
│   ├── conversation.py            # Conversation management
│   ├── splash_screen.py           # Startup screen
│   ├── providers/                 # Multi-Provider System
│   │   ├── base.py                # Abstract provider interface
│   │   ├── groq.py                # Groq provider
│   │   ├── openai.py              # OpenAI provider
│   │   ├── anthropic.py           # Anthropic provider
│   │   ├── google.py              # Google provider
│   │   ├── openrouter.py          # OpenRouter aggregator
│   │   ├── mistral.py             # Mistral provider
│   │   ├── together.py            # Together AI provider
│   │   ├── deepseek.py            # DeepSeek provider
│   │   └── cohere.py              # Cohere provider
│   ├── config/                    # Configuration System
│   │   ├── api_detector.py        # Auto-detect provider from API key
│   │   ├── provider_config.py     # Multi-provider config manager
│   │   └── model_registry.py      # Model caching and discovery
│   ├── prompts/                   # Prompt Optimization
│   │   ├── base.py                # Base prompt templates
│   │   └── variants.py            # Model family-specific prompts
│   ├── commands/                  # CLI Commands
│   │   ├── provider_commands.py   # Provider management
│   │   └── model_commands.py      # Model management
│   └── tools/                     # Function Calling Tools
│       ├── file_ops.py            # File operations
│       ├── bash.py                # System commands
│       ├── search.py              # Search tools
│       ├── git.py                 # Git integration
│       └── [more...]
├── iabuilder-cli                  # Main executable script
├── install_iabuilder.sh           # Installation script
└── README.md
```

## 🗜️ Context Compression

Like Claude Code, IABuilder features intelligent context compression:

- **Automatic compression** every 50k tokens
- **Preserves** important decisions and file operations
- **Seamless continuation** without restarting
- **Compressed storage** in `~/.iabuilder/resume/`

### Commands:
```bash
/compress              # Manual compression
/stats                 # View compression statistics
/resume [session_id]   # Load compressed session
```

## ⚙️ Configuration

Configuration is stored in `~/.iabuilder/`:

```
~/.iabuilder/
├── config.yaml          # Main configuration
├── providers.yaml       # Provider API keys (encrypted)
├── model_cache.json     # Cached model listings
├── history/             # Conversation history
└── resume/              # Compressed sessions
```

### config.yaml
```yaml
default_model: llama-3.3-70b-versatile
max_tokens: 8000
temperature: 0.7
auto_save: true
safe_mode: false
```

### providers.yaml (managed via commands)
```yaml
providers:
  groq:
    api_key: gsk_xxxxx
    base_url: https://api.groq.com/openai/v1
    active: true
  openai:
    api_key: sk-xxxxx
    base_url: https://api.openai.com/v1
    active: true
```

## 🎨 Examples

### Example 1: Multi-Provider Workflow

```bash
# Start with Groq for fast iteration
/model llama-3.1-8b-instant
> Create a Python script that processes CSV files

# Switch to GPT-4 for complex logic
/model gpt-4
> Optimize the algorithm for large files

# Switch to Claude for documentation
/model claude-opus-4
> Write comprehensive documentation for this module

# Back to Groq for testing
/model llama-3.3-70b-versatile
> Create unit tests for all functions
```

### Example 2: Provider Setup

```bash
# Day 1: Setup Groq (free, fast)
/configure-api groq
> Enter API key: gsk_xxxxxxxxxxxxx
✅ Groq configured successfully

# Day 2: Add OpenAI (more powerful)
/configure-api openai
> Enter API key: sk-xxxxxxxxxxxxxx
✅ OpenAI configured successfully

# Day 3: Add Anthropic (best for coding)
/configure-api anthropic
> Enter API key: sk-ant-xxxxxxxxxxxxx
✅ Anthropic configured successfully

# Now you have access to all models!
/models
```

### Example 3: Project-Aware Development

```bash
cd ~/my-web-app

iabuilder
# IABuilder automatically detects:
# - Node.js project (package.json)
# - Git repository (.git/)
# - React files (src/)

> Read package.json and show me what dependencies are outdated
> Create a new React component in src/components/UserProfile.jsx
> Run npm test and fix any failing tests
> Commit the changes with a descriptive message
```

## 🔒 Security & Safety

- ✅ File operations validate paths (no directory traversal)
- ✅ Bash commands run with timeouts
- ✅ Config files have secure permissions (600)
- ✅ API keys stored with base64 encoding
- ✅ Safe mode available for destructive operations
- ⚠️ **Production note**: Use real encryption for API keys

## 🆚 Comparison

| Feature | IABuilder | Claude Code | Cursor | Zed |
|---------|-----------|-------------|--------|-----|
| **Multi-Provider** | ✅ 9+ providers | ❌ Anthropic only | ❌ OpenAI only | ❌ Custom only |
| **Terminal-First** | ✅ | ✅ | ❌ (GUI) | ❌ (GUI) |
| **Function Calling** | ✅ Atomic tools | ✅ | ✅ | ✅ |
| **Context Compression** | ✅ | ✅ | ❌ | ❌ |
| **Project-Aware** | ✅ | ✅ | ✅ | ✅ |
| **Model Switching** | ✅ Cross-provider | ❌ | ❌ | ✅ Limited |
| **Cost** | Free/BYOK | Free tier + paid | Paid | Free |
| **Offline** | ❌ | ❌ | ❌ | ✅ Partial |

## 🚀 Roadmap

### Completed (Version 3.0) ✅
- [x] Multi-provider architecture
- [x] 9 provider integrations
- [x] Model registry with caching
- [x] Prompt optimization per model family
- [x] Provider/model management commands
- [x] Rename to IABuilder

### Future Enhancements
- [ ] Real encryption for API keys (currently base64)
- [ ] Plugin system for custom providers
- [ ] Conversation templates
- [ ] Code snippets library
- [ ] Model benchmarking
- [ ] Parallel model requests
- [ ] Custom model fine-tuning integration
- [ ] Team collaboration features

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Credits

- Inspired by **Anthropic's Claude Code** and **Cursor**
- Built with **Groq**, **OpenAI**, **Anthropic**, **Google**, and other LLM APIs
- Uses **prompt-toolkit** for rich CLI experience
- Powered by **tiktoken** for token counting

## 📧 Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Documentation: [Full docs](./docs/)

---

**Made with ❤️ for developers who want universal AI assistance without vendor lock-in.**
