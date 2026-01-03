# Rill (Prototype)

Rill is a beginner-first programming language designed around **explicitness** and **teachability** (e.g., `set` vs `change`, explainable execution, table-first data in later milestones).

This repository is a **single master repo** for all Rill work (lexer → parser → interpreter → future features).

---

## Current status

### Implemented (v0)
- **Lexer**
  - Keywords/identifiers, numbers, strings (`'` or `"` with escapes), comments (`# ...`)
  - Operators/punctuation including `%`, `!=`, `<=`, `>=`
  - Emits `NEWLINE` tokens and an `EOF` token
  - Tracks source spans (line/col + indices)
  - Reads files as `utf-8-sig` (handles Windows UTF-8 BOM)

- **Parser**
  - Statements: `show`, `set … to …`, `change … to …`
  - Assignment targets: `name` and `name[index]`
  - Expressions with precedence: unary (`not`, unary `-`), `* / %`, `+ -`, comparisons, `and`, `or`, grouping, indexing

- **Interpreter**
  - Runs the same v0 subset: `show`, `set`, `change`
  - Value types in v0: `number`, `text`, `boolean`, `empty`
  - Strict typing (no silent coercion)

### Not implemented yet
- `if` / `repeat` / `define` / `give back`
- records/maps/tables (syntax and runtime)
- `trace` / `explain` modes
- file module (`file.load` / `file.save`)
- testing blocks (`check` / `expect`)

---

## Quickstart (Windows PowerShell)

### Setup
```powershell
cd Rill
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

### Create a sample program
```powershell
@"
set x to 2 + 3 * 4
show x
change x to x + 1
show x % 2
"@ | Set-Content .\example.rill -Encoding utf8
```

### Run
```powershell
# print tokens
py -m rill.cli tokens .\example.rill

# print AST
py -m rill.cli parse .\example.rill

# execute (interpreter v0)
py -m rill.cli run .\example.rill
```

Expected output for `run`:
```
14
1
```

### Run tests
```powershell
py -m pytest
```

---

## CLI behavior

The CLI supports subcommands:

- `tokens <file>` — tokenize and print tokens
- `parse <file>` — parse and print the AST
- `run <file>` — parse and execute (v0 subset)

Backward-compatible form:
- `py -m rill.cli <file>` defaults to `tokens`

---

## Repository layout

```
rill/                 # Python package
  lexer.py
  parser.py
  interpreter.py
  token.py
  ast.py
  runtime.py
  cli.py
tests/
examples/             # (optional) add sample .rill programs here
```

---

## Milestone tags

Milestones are tracked via annotated git tags:

- `v0-lexer`
- `v0-parser`
- (next) `v0-interpreter`

To push tags to GitHub:
```powershell
git push --tags
```

---

## Roadmap (near-term)

1. **Interpreter v0 completeness**
   - Better runtime errors (friendlier messages)
   - More expression forms as needed by upcoming syntax

2. **Control flow**
   - `if / otherwise / end`
   - `repeat …` (times / while / range with `step` rules)

3. **Functions**
   - `define … taking …`
   - `give back`

4. **Data structures + tables**
   - records vs maps
   - table operators and aggregates

5. **Differentiators**
   - `trace` and `explain` execution modes
   - teaching-grade error messages

---

## Notes

- This repo intentionally avoids multiple sub-repos. Lexer/parser/interpreter live together and share tokens/AST.
- The language spec (Draft 4.1+) is maintained as a separate markdown document; consider adding it under `spec/` in this repo for convenience.
