"""Project exploration and context management for Zed-like experience."""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class ProjectExplorer:
    """Explores project structure and provides context like Zed."""

    def __init__(self, working_directory: Path):
        self.working_directory = working_directory
        self.project_context: Dict[str, Any] = {}
        self.file_index: Dict[str, List[Path]] = {}
        self.references: Dict[str, Any] = {}

    def explore_project(self) -> Dict[str, Any]:
        """Explore the entire project structure like Zed does automatically."""
        print("🔍 Exploring project structure...")

        # Basic project info
        self.project_context = {
            "working_directory": str(self.working_directory),
            "project_name": self.working_directory.name,
            "exploration_time": datetime.now().isoformat(),
            "total_files": 0,
            "total_dirs": 0,
            "languages": set(),
            "frameworks": set(),
            "has_git": (self.working_directory / ".git").exists(),
            "has_readme": self._find_readme(),
            "has_package_json": (self.working_directory / "package.json").exists(),
            "has_requirements": self._find_requirements(),
            "has_docker": (self.working_directory / "Dockerfile").exists(),
        }

        # Explore directory structure
        self._explore_directory(self.working_directory)

        # Index files by type
        self._index_files_by_type()

        # Set up intelligent references
        self._setup_references()

        # Include file index in returned context
        self.project_context["file_index"] = self.file_index

        print(f"✅ Project explored: {self.project_context['total_files']} files, {len(self.project_context['languages'])} languages")
        return self.project_context

    def _explore_directory(self, directory: Path, max_depth: int = 3, current_depth: int = 0):
        """Recursively explore directory structure."""
        if current_depth > max_depth:
            return

        try:
            for item in directory.iterdir():
                if item.is_file():
                    self.project_context["total_files"] += 1
                    self._analyze_file(item)
                elif item.is_dir() and not self._should_skip_dir(item):
                    self.project_context["total_dirs"] += 1
                    self._explore_directory(item, max_depth, current_depth + 1)
        except PermissionError:
            pass  # Skip directories we can't read

    def _should_skip_dir(self, directory: Path) -> bool:
        """Check if directory should be skipped during exploration."""
        skip_dirs = {
            "__pycache__", ".git", "node_modules", ".next", ".nuxt",
            "dist", "build", ".vscode", ".idea", "venv", "env",
            ".venv", ".env", "target", ".gradle", "bin", "obj"
        }
        return directory.name in skip_dirs or directory.name.startswith(".")

    def _analyze_file(self, file_path: Path):
        """Analyze individual file for language/framework detection."""
        extension = file_path.suffix.lower()
        name = file_path.name.lower()

        # Language detection
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".vue": "vue",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".sql": "sql",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
        }

        if extension in language_map:
            self.project_context["languages"].add(language_map[extension])

        # Framework detection
        if name == "package.json":
            self._detect_js_framework(file_path)
        elif name in ["requirements.txt", "setup.py", "pyproject.toml"]:
            self._detect_python_framework(file_path)

    def _detect_js_framework(self, package_json: Path):
        """Detect JavaScript/TypeScript frameworks."""
        try:
            import json
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})

                # React
                if "react" in deps:
                    self.project_context["frameworks"].add("react")
                # Vue
                if "vue" in deps:
                    self.project_context["frameworks"].add("vue")
                # Angular
                if "@angular/core" in deps:
                    self.project_context["frameworks"].add("angular")
                # Next.js
                if "next" in deps:
                    self.project_context["frameworks"].add("nextjs")
                # Express
                if "express" in deps:
                    self.project_context["frameworks"].add("express")
                # NestJS
                if "@nestjs/core" in deps:
                    self.project_context["frameworks"].add("nestjs")
        except:
            pass

    def _detect_python_framework(self, requirements_file: Path):
        """Detect Python frameworks."""
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()

                frameworks = {
                    "django": "django",
                    "flask": "flask",
                    "fastapi": "fastapi",
                    "tornado": "tornado",
                    "bottle": "bottle",
                    "pyramid": "pyramid",
                }

                for package, framework in frameworks.items():
                    if package in content:
                        self.project_context["frameworks"].add(framework)
        except:
            pass

    def _find_readme(self) -> Optional[str]:
        """Find README file."""
        readme_names = ["README.md", "README.txt", "README.rst", "readme.md"]
        for name in readme_names:
            if (self.working_directory / name).exists():
                return name
        return None

    def _find_requirements(self) -> Optional[str]:
        """Find Python requirements file."""
        req_names = ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"]
        for name in req_names:
            if (self.working_directory / name).exists():
                return name
        return None

    def _index_files_by_type(self):
        """Index files by type for quick access."""
        try:
            all_files = list(self.working_directory.rglob("*"))
            all_files = [f for f in all_files if f.is_file()][:1000]  # Limit for performance

            for file_path in all_files:
                if self._should_skip_dir(file_path.parent):
                    continue

                extension = file_path.suffix.lower()
                name = file_path.name.lower()

                # Index by extension
                if extension not in self.file_index:
                    self.file_index[extension] = []
                self.file_index[extension].append(file_path)

                # Special categories
                if name in ["package.json", "requirements.txt", "setup.py", "cargo.toml"]:
                    if "config" not in self.file_index:
                        self.file_index["config"] = []
                    self.file_index["config"].append(file_path)

        except Exception as e:
            print(f"Warning: File indexing failed: {e}")


    def _setup_references(self):
        """Setup intelligent references like Zed."""
        self.references = {
            "mi proyecto": self.working_directory,
            "esta carpeta": self.working_directory,
            "el proyecto": self.working_directory,
            "aquí": self.working_directory,
            "este directorio": self.working_directory,
        }

        # Setup file type references
        if ".html" in self.file_index and self.file_index[".html"]:
            html_files = self.file_index[".html"]
            self.references["el archivo html"] = html_files[0] if html_files else None  # Single file for general reference
            self.references["los archivos html"] = html_files

        if ".py" in self.file_index and self.file_index[".py"]:
            py_files = [f for f in self.file_index[".py"] if not f.name.startswith("__")]
            if py_files:
                self.references["mi código python"] = py_files[:5]  # Top 5 files
                self.references["los archivos python"] = py_files

        if ".js" in self.file_index and self.file_index[".js"]:
            js_files = self.file_index[".js"]
            self.references["mi código javascript"] = js_files[:5]

        # README reference
        if self.project_context.get("has_readme"):
            readme_path = self.working_directory / self.project_context["has_readme"]
            self.references["el readme"] = readme_path
            self.references["la documentación"] = readme_path

    def resolve_reference(self, user_input: str) -> Optional[Any]:
        """Resolve vague references to concrete paths/files."""
        user_input_lower = user_input.lower()

        # Direct references
        for ref, value in self.references.items():
            if ref in user_input_lower:
                return value

        # File type references
        if "html" in user_input_lower and ".html" in self.file_index:
            return self.file_index[".html"][0] if len(self.file_index[".html"]) == 1 else self.file_index[".html"]

        if "python" in user_input_lower and ".py" in self.file_index:
            py_files = [f for f in self.file_index[".py"] if not f.name.startswith("__")]
            return py_files[0] if len(py_files) == 1 else py_files[:3]

        if "javascript" in user_input_lower and ".js" in self.file_index:
            return self.file_index[".js"][0] if len(self.file_index[".js"]) == 1 else self.file_index[".js"][:3]

        return None

    def get_project_summary(self) -> str:
        """Get a human-readable project summary like Zed shows."""
        summary = f"""
📁 **PROJECT: {self.project_context['project_name']}**
🏠 **Location:** {self.project_context['working_directory']}
📊 **Size:** {self.project_context['total_files']} files, {self.project_context['total_dirs']} directories

🛠️ **Tech Stack:**
• **Languages:** {', '.join(sorted(self.project_context['languages'])) if self.project_context['languages'] else 'Unknown'}
• **Frameworks:** {', '.join(sorted(self.project_context['frameworks'])) if self.project_context['frameworks'] else 'None detected'}

📋 **Key Files:**
{self._get_key_files_summary()}

🔍 **Available References:**
• "mi proyecto/esta carpeta" → {self.working_directory.name}
• "el archivo html" → {self._get_html_files_summary()}
• "mi código python" → {len([f for f in self.file_index.get('.py', []) if not f.name.startswith('__')])} files
• "el readme" → {self.project_context.get('has_readme', 'None')}
"""

        return summary.strip()

    def _get_key_files_summary(self) -> str:
        """Get summary of key project files."""
        key_files = []

        if self.project_context.get("has_readme"):
            key_files.append(f"📖 README: {self.project_context['has_readme']}")

        if self.project_context.get("has_package_json"):
            key_files.append("📦 package.json (JavaScript/Node.js)")

        if self.project_context.get("has_requirements"):
            key_files.append(f"🐍 Requirements: {self.project_context['has_requirements']}")

        if self.project_context.get("has_docker"):
            key_files.append("🐳 Dockerfile (Containerized)")

        if self.project_context.get("has_git"):
            key_files.append("🌿 .git (Git repository)")

        return "\n".join(f"• {file}" for file in key_files) if key_files else "• No key files detected"

    def _get_html_files_summary(self) -> str:
        """Get summary of HTML files."""
        if ".html" not in self.file_index:
            return "None found"

        html_files = self.file_index[".html"]
        if len(html_files) == 1:
            return html_files[0].name
        elif len(html_files) <= 3:
            return ", ".join(f.name for f in html_files)
        else:
            return f"{len(html_files)} files (index.html, about.html, etc.)"