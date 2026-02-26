import os
from pathlib import Path


IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
VALID_EXTENSIONS = (".py", ".md", ".yaml", ".yml", ".json", ".ts", ".js")


def load_readme() -> str:
    readme = Path("README.md")
    if readme.exists():
        return readme.read_text(encoding="utf-8")
    return ""


def load_code_context(max_chars: int = 12000) -> str:
    chunks = []

    for root, dirs, files in os.walk("."):
        # Remove ignored directory
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file.endswith(VALID_EXTENSIONS):
                file_path = Path(root) / file

                try:
                    content = file_path.read_text(encoding="utf-8")
                    chunks.append(
                        f"\n\n### File: {file_path}\n{content[:1500]}"
                    )
                except Exception:
                    continue

    combined = "\n".join(chunks)
    return combined[:max_chars]