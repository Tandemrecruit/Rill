# Rill v0 — Lexer Prototype

This package is a minimal, implementation-ready lexer for the Rill language spec (Draft 4.1+).
It tokenizes:
- keywords, identifiers
- numbers
- strings (single or double quotes) with escapes
- operators/punctuation
- comments (`# ...`)
- newline tokens (statement separators)

## Setup (Windows PowerShell)

```powershell
cd rill_v0_lexer
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

## Run the lexer on a file

```powershell
py -m rill.cli path\to\program.rill
```

## Run tests

```powershell
py -m pytest
```

## Notes

- Blocks use `end` in the spec, so we do **not** implement Python-style INDENT/DEDENT tokens.
- Newlines are emitted as `NEWLINE` tokens (unless inside strings).
