# Intelligent Code Reviewer & Explainer

**DecodeLabs Generative AI Internship — Project 4**

A command-line developer tool that reads a code file, finds bugs, explains the code in plain language and suggests an optimized version — printed in the terminal with **syntax highlighting**.

## Example
```bash
python reviewer.py examples/buggy_cart.py
```
The report always has three sections:

| Section | Content |
|---------|---------|
| `## EXPLANATION` | What the code does, in 2–4 plain sentences |
| `## BUG_REPORT` | Bullet points tagged `[CRITICAL]`, `[MAJOR]` or `[MINOR]` |
| `## REFACTORED_CODE` | One complete, corrected code block |

## How It Works
```
1. Ingest          2. Analyze                     3. Validate                  4. Render
read file as   →   Gemini + strict system    →   all 3 sections present?  →  rich Markdown with
raw string         instruction, temp 0.1         exactly 1 code block?        colour syntax highlighting
                                                 retry once if not
```

1. **Safe file ingestion** — the file is read as a raw string with whitespace and indentation preserved. Clear errors for missing files, folders, no permission, empty files, binary files and unsupported types. Non-UTF-8 files fall back to Latin-1 instead of crashing.
2. **Strict system instruction** — the model acts as an analytical QA engineer: no greetings or filler, a fixed section order, severity tags, and a single code block. Temperature is set to `0.1` for consistent output.
3. **Output validation** — the response is rejected unless it contains all three sections in order, bullet points in the bug report, and exactly one fenced code block in the refactored section. If it fails, the tool asks the model again with the reason; a malformed report is never shown.
4. **Rendering** — the Markdown is rendered with `rich`, so code blocks get colour syntax highlighting in the terminal. `--save` also writes the report to `reports/`.

**Supported languages:** Python, JavaScript, TypeScript, Java, C, C++, C#, Go, PHP, Ruby, Rust, Kotlin, Swift, SQL.

## Setup
```bash
git clone https://github.com/Moemenakari/code-reviewer.git
cd code-reviewer
pip install -r requirements.txt
```
Create a `.env` file (copy `.env.example`) with your free key from [Google AI Studio](https://aistudio.google.com/apikey):
```
GEMINI_API_KEY=your_api_key_here
```

## Usage
```bash
python reviewer.py examples/buggy_cart.py           # Python example with 5+ bugs
python reviewer.py examples/user_search.js --save   # JavaScript example, saves the report
python reviewer.py path/to/your_file.java
```

## Tests
Tests use a fake client, so no API key is needed:
```bash
python -m unittest test_reviewer.py
```
They cover file reading and error handling, encoding fallback, report validation (missing sections, extra code blocks, chatty answers), and the retry when the model breaks the format.

## Project Structure
```
reviewer.py          file ingestion, prompt, validation, rendering, CLI
examples/            sample files with intentional bugs
test_reviewer.py     unit tests
```

## Tech Stack
Python · Google Gemini API (`google-genai`) · Rich

## Author
**Mouemen Akkarie** — [GitHub](https://github.com/Moemenakari)
