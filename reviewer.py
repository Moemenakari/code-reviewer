"""
Intelligent Code Reviewer & Explainer

Reads a code file, sends it to Gemini with strict instructions, and prints a
colour-highlighted report with three sections:
  - EXPLANATION      what the code does, in plain language
  - BUG_REPORT       bugs, risks and performance issues as bullet points
  - REFACTORED_CODE  one corrected, optimized code block

Usage:
  python reviewer.py examples/buggy_cart.py
  python reviewer.py my_script.js --save
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_FILE_CHARS = 60_000  # keep the payload inside the model's context budget

LANGUAGES = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".go": "go", ".php": "php",
    ".rb": "ruby", ".rs": "rust", ".kt": "kotlin", ".swift": "swift", ".sql": "sql",
}

REQUIRED_SECTIONS = ["## EXPLANATION", "## BUG_REPORT", "## REFACTORED_CODE"]

SYSTEM_INSTRUCTION = """You are a strict, analytical Senior Code Quality Assurance Engineer.
Never write greetings, small talk or closing remarks.
Your answer must contain exactly these three Markdown sections, in this order:

## EXPLANATION
2-4 short sentences in plain language explaining what the code does.

## BUG_REPORT
Only bullet points. Each bullet starts with a severity tag: [CRITICAL], [MAJOR] or [MINOR],
then the line or function, then the problem and why it matters.
Cover syntax errors, logic bugs, edge cases, security risks and performance issues.
If there are no bugs, write a single bullet: "- [NONE] No issues found."

## REFACTORED_CODE
Exactly one fenced code block with the language tag, containing the full corrected code.
Keep the original behaviour, fix every reported bug, and add short comments where you changed something."""


class ReviewError(Exception):
    """Errors with a message that is safe to show to the user."""


def read_code_file(path):
    """Load the file as a string, keeping all whitespace and indentation exactly."""
    file = Path(path)
    language = LANGUAGES.get(file.suffix.lower())
    if not language:
        raise ReviewError(f"Unsupported file type '{file.suffix}'. Supported: {', '.join(LANGUAGES)}")
    try:
        code = file.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ReviewError(f"File not found: {path}")
    except PermissionError:
        raise ReviewError(f"No permission to read: {path}")
    except IsADirectoryError:
        raise ReviewError(f"That is a folder, not a file: {path}")
    except UnicodeDecodeError:
        # Some files use older encodings; fall back instead of crashing
        code = file.read_text(encoding="latin-1")
        if "\x00" in code:
            raise ReviewError("This looks like a binary file, not source code.")

    if not code.strip():
        raise ReviewError("The file is empty.")
    if len(code) > MAX_FILE_CHARS:
        raise ReviewError(f"File is too large ({len(code)} chars). Limit is {MAX_FILE_CHARS}.")
    return code, language, file.name


def build_prompt(code, language, filename):
    return (f"Review this {language} file named `{filename}`.\n\n"
            f"```{language}\n{code}\n```")


def validate_report(report):
    """Reject the answer unless it has every section and exactly one code block in REFACTORED_CODE."""
    missing = [s for s in REQUIRED_SECTIONS if s not in report]
    if missing:
        return False, f"missing section(s): {', '.join(missing)}"

    positions = [report.index(s) for s in REQUIRED_SECTIONS]
    if positions != sorted(positions):
        return False, "sections are in the wrong order"

    refactored = report.split("## REFACTORED_CODE", 1)[1]
    blocks = re.findall(r"```[\w+#-]*\n.*?```", refactored, flags=re.DOTALL)
    if len(blocks) != 1:
        return False, f"REFACTORED_CODE must have exactly one code block (found {len(blocks)})"

    bugs = report.split("## BUG_REPORT", 1)[1].split("## REFACTORED_CODE", 1)[0]
    if not re.search(r"^\s*[-*] ", bugs, flags=re.MULTILINE):
        return False, "BUG_REPORT has no bullet points"
    return True, ""


def review_code(client, code, language, filename, max_attempts=2):
    """Ask the model for a review. If the format is wrong, ask once more before giving up."""
    prompt = build_prompt(code, language, filename)
    reason = ""
    for _ in range(max_attempts):
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1,  # low = consistent, analytical output
            ),
        )
        report = (response.text or "").strip()
        ok, reason = validate_report(report)
        if ok:
            return report
        prompt = (build_prompt(code, language, filename)
                  + f"\n\nYour previous answer was rejected because: {reason}. "
                    "Follow the required format exactly.")
    raise ReviewError(f"The model did not return a valid report ({reason}).")


def save_report(report, filename):
    folder = Path("reports")
    folder.mkdir(exist_ok=True)
    path = folder / f"{Path(filename).stem}_review_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(f"# Code Review: {filename}\n\n{report}\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI code reviewer and explainer.")
    parser.add_argument("file", help="Path to a code file (.py, .js, .java, ...)")
    parser.add_argument("--save", action="store_true", help="Also save the report as Markdown in reports/")
    args = parser.parse_args(argv)

    console = Console()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Missing GEMINI_API_KEY. Copy .env.example to .env and add your key.[/red]")
        sys.exit(1)

    try:
        code, language, filename = read_code_file(args.file)
        console.print(Panel(f"Reviewing [bold]{filename}[/bold] ({language}, {len(code.splitlines())} lines)",
                            style="cyan"))
        with console.status("Analyzing code..."):
            report = review_code(genai.Client(api_key=api_key), code, language, filename)
    except ReviewError as error:
        console.print(f"[red]Error:[/red] {error}")
        sys.exit(1)

    console.print(Markdown(report, code_theme="monokai"))
    if args.save:
        console.print(f"\n[green]Saved to {save_report(report, filename)}[/green]")


if __name__ == "__main__":
    main()
