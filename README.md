# Rill v0 — Lexer + Parser Prototype

This package is a minimal lexer + parser prototype for the Rill language spec (Draft 4.1+).

It currently supports:
- lexing (tokens)
- parsing (AST) for a v0 subset: `show`, `set ... to ...`, `change ... to ...` and expressions

The lexer tokenizes:
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

## Print tokens

```powershell
py -m rill.cli tokens path\to\program.rill

# backward compatible (defaults to tokens)
py -m rill.cli path\to\program.rill
```

## Parse and print the AST

```powershell
py -m rill.cli parse path\to\program.rill
```

## Run tests

```powershell
py -m pytest
```

## Notes

- Blocks use `end` in the spec, so we do **not** implement Python-style INDENT/DEDENT tokens.
- Newlines are emitted as `NEWLINE` tokens (unless inside strings).
