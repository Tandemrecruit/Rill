# Rill (Prototype)

Rill is a beginner-first programming language designed around readable, English-like syntax, explainable execution, and (in later milestones) table-first data operations.

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
  - Statements:
    - `show …`
    - `set <name> to …`
    - `change <name> to …`
    - `if …` / `otherwise` / `end`
    - `repeat … times` / `repeat while …` / `end`
    - `stop` / `skip` (loop control)
  - Assignment targets: `name` and `name[index]`
  - Expressions with precedence: unary (`not`, unary `-`), `* / %`, `+ -`, comparisons, `and`, `or`, grouping, indexing

- **Interpreter**
  - Executes the v0 language subset above (including `if` / `repeat` / `stop` / `skip`)
  - Value types in v0: `number`, `text`, `boolean`, `empty`
  - Strict typing (no silent coercion)

### Not implemented yet
- Functions: `define … taking …` / `give back`
- records/maps/tables (syntax and runtime)
- `trace` / `explain` modes
- file module (`file.load` / `file.save`)
- testing blocks (`check` / `expect`)
- additional loop forms (e.g., `repeat … from … to … step …`)

---

## Quickstart (Windows PowerShell)

### Setup
```powershell
cd <repo-folder>
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

### Create a sample program
```powershell
@"
set x to 0

repeat 5 times
    change x to x + 1
end

if x = 5
    show "ok"
otherwise
    show "bad"
end
"@ | Set-Content .\example.rill -Encoding utf8 
```

### Run
```powershell
# print tokens
py -m rill tokens .\example.rill

# print AST
py -m rill parse .\example.rill

# execute
py -m rill run .\example.rill
```
Expected output for `run`:
```nginx
ok
```

### Run tests
```powershell
py -m pytest
```

---

## CLI Behavior

The CLI supports subcommands:
- `tokens <file>` — tokenize and print tokens
- `parse <file>` — parse and print AST
- `run <file>` — parse and execute (v0 subset)

Entry points (all equivalent when installed with `pip install -e`):

- `py -m rill <subcommand> <file>`

- `rill <subcommand> <file>`

- `py -m rill.cli <subcommand> <file>`

Backward-compatible form:

- `py -m rill.cli <file>` defaults to `tokens`
---
## Repository layout
```bash
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
Milestones are tracked via annotated git tags (recommended format: `v0-<milestone>`):
- `v0-lexer`
- `v0-parser`
- `v0-interpreter`
- `v0-control-flow`

To push tags to Github:
```powershell
git push --tags
```
---
## Roadmap (near-term)
1. Interpreter polish
    - Better runtime errors (friendlier messages)

    - More expression forms as needed by upcoming syntax

2. More loop forms

    - repeat … from … to … step … (range/step rules)

3. Functions

    - define … taking …

    - give back

4. Data structures + tables

    -records vs maps

    - table operators and aggregates

5. Differentiators

    - trace and explain execution modes

    - teaching-grade error messages
---
## Notes
- This repo intentionally avoids multiple sub-repos. Lexer/parser/interpreter live together and share tokens/AST.