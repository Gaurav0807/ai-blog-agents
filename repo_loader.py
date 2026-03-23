import os
from pathlib import Path
import subprocess

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
VALID_EXTENSIONS = (".py", ".md", ".yaml", ".yml", ".json", ".ts", ".js")





def get_last_blog_commit():
    from pathlib import Path

    if not Path("medium_blog.md").exists():
        return None

    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", "medium_blog.md"]
        ).decode().strip()
    except:
        return None


def load_existing_blog():
    from pathlib import Path

    path = Path("medium_blog.md")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_git_changes(trigger_sha: str):
    last_commit = get_last_blog_commit()

    if not last_commit:
        # First run
        commits = subprocess.check_output(
            ["git", "log", "-n", "20", "--pretty=format:%h - %s"]
        ).decode()

        diff = subprocess.check_output(
            ["git", "diff"]
        ).decode()

        return commits, diff

    # Incremental mode
    commits = subprocess.check_output(
        ["git", "log", f"{last_commit}..{trigger_sha}", "--pretty=format:%h - %s"]
    ).decode()

    diff = subprocess.check_output(
        ["git", "diff", f"{last_commit}..{trigger_sha}"]
    ).decode()

    return commits, diff


def load_readme() -> str:
    readme = Path("README.md")
    if readme.exists():
        return readme.read_text(encoding="utf-8")
    return ""


def load_code_context(max_chars=None) -> str:
    chunks = []

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file.endswith(VALID_EXTENSIONS):
                file_path = Path(root) / file

                try:
                    content = file_path.read_text(encoding="utf-8")
                    chunks.append(
                        f"\n\n### File: {file_path}\n{content}"
                    )
                except Exception:
                    continue

    combined = "\n".join(chunks)

    if max_chars:
        return combined[:max_chars]

    return combined