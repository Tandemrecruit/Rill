# Rill Programming Language — v1 Specification (Draft)



## 1. Purpose

Rill is a beginner-first programming language designed to teach core programming concepts without intimidation, while still being useful for real tasks (especially small automation and data work).

### Design goals
- **Zero intimidation:** readable like instructions; minimal punctuation; no boilerplate.
- **Transferable concepts:** variables, data structures, functions, control flow, files, testing.
- **Safe by default:** avoids common beginner pitfalls (implicit coercions, accidental variable creation).
- **Immediate feedback:** REPL + step-by-step execution options.
- **Worth learning:** explainable execution, table-first data, guided errors, built-in checks.

### Non-goals (v1)
- High-performance systems work
- Complex metaprogramming
- Manual memory management
- Exception/try-catch style error handling

---

## 2. Execution model and tooling

### 2.1 Modes
- **REPL:** run lines immediately.
- **Script:** run `.rill` files top-to-bottom.
- **Notebook cells (optional tooling):** same language, chunked execution.

### 2.2 Explainable runtime
Programs can run in three modes:
- `run`: normal.
- `trace`: shows variable changes and branch decisions.
- `explain`: adds short plain-language explanations per line and per branch choice.

---

## 3. Surface syntax

### 3.1 Statements and whitespace
- One statement per line.
- Newline ends a statement.
- Indentation is recommened for readability; blocks are delimited by `end` (v0), may be enforced later.

### 3.2 Blocks (**`end` is required**)
Blocks begin with a header line and end with a matching `end`.

- `end` must appear at the same indentation level as the block header.
- `otherwise` / `otherwise if` must align with the matching `if`.

```rill
if score >= 10
    show "Win!"
otherwise
    show "Try again."
end
```

### 3.3 Keywords are verbs
Core keywords:
- `set`, `change`, `if`, `otherwise`, `repeat`, `for each`, `define`, `give back`, `show`, `ask`,
  `stop`, `skip`, `use`, `check`, `expect`

### 3.4 Comments
- A comment starts with `#` and continues to end of line.
- Inline comments are allowed:

```rill
set x to 10  # initial value
```

`#` inside a string literal is not a comment.

---

## 4. Strings (quotes and escaping)

### 4.1 Quote styles
Rill supports **both** double-quoted and single-quoted strings:

```rill
set a to "It's working"
set b to 'She said "hello"'
```

### 4.2 Escapes
Inside either quote style, Rill supports backslash escapes:

- `\` backslash
- `\n` newline
- `\t` tab
- `\r` carriage return
- `\"` double quote (only needed inside `"..."`)
- `\'` single quote (only needed inside `'...'`)

Example:
```rill
set message to "She said \"hello\""
```

Unrecognized escape sequences are errors with a suggested fix.

---

## 5. Values and types

### 5.1 Built-in types
- `number` (integers + decimals)
- `text`
- `boolean` (`true` / `false`)
- `list`
- `map` (key/value dictionary)
- `record` (named fields; structured data)
- `table` (rows/columns; see section 12)
- `empty` (explicit “no value”)

### 5.2 Literals
- Numbers: `12`, `3.14`
- Text: `"hello"`, `'hello'`
- Booleans: `true`, `false`
- List: `[1, 2, 3]`
- Record: `{name: "Ava", age: 12}` (unquoted identifier keys)
- Map: `{"theme": "dark", "retry": 3}` (quoted text keys)
- Table: `table [ {…}, {…} ]`
- Empty list: `[]`

### 5.3 Record vs map rule (explicit)
- **Keys without quotes create a `record`.**
- **Keys with quotes create a `map`.**
- **Mixing key styles is an error** in v1.

```rill
set bad to {name: "Ava", "age": 12}  # ERROR: cannot mix record keys and map keys
```

### 5.4 Empty records and empty maps (**no `{}` ambiguity**)
Because `{}` would be ambiguous, v1 requires explicit constructors:

- `empty record`
- `empty map`

Examples:
```rill
set r to empty record
set m to empty map
```

(Optionally, for readability only: `record {}` and `map {}` are synonyms for `empty record` and `empty map`.)

### 5.5 No silent type coercion
Rill does not silently convert types.

- `"3" + 4` is an error with suggestions.
- Conversions are explicit (section 9).

---

## 6. Variables, assignment, and scope

### 6.1 `set` vs `change`
- `set` creates a variable in the current scope.
- `change` updates an existing variable (nearest enclosing scope).

Errors:
- `set x to …` when `x` already exists in the current scope → error (“Use `change` to update.”)
- `change x to …` when `x` does not exist in any enclosing scope → error (“Use `set` to create first.”)

### 6.2 Scope rules (**safe by default**)
Rill uses lexical scoping with **block scope**:
- `define … end` creates a function scope.
- Any block (`if`, `repeat`, `for each`, `check`) creates an inner scope.

---

## 7. Operators, comparisons, and precedence

### 7.1 Core operators
- Math: `+ - * /`
- Comparisons: `= != < <= > >=`
- Boolean: `and or not`

### 7.2 Closed set of readable comparison sugar (v1)
- `is` → `=`
- `is not` → `!=`
- `is at least` → `>=`
- `is at most` → `<=`
- `is empty` / `is not empty` (section 7.3)

### 7.3 `empty` comparisons
```rill
if result is empty
    show "No result"
end

if result is not empty
    show "Has result"
end
```

### 7.4 Operator precedence (highest to lowest)
1. Parentheses: `( … )`
2. Postfix access/call: `()`, `[]`, `.field`
3. Unary: `not`, unary `-`
4. Multiplication/division: `*` `/`
5. Addition/subtraction: `+` `-`
6. Comparisons: `= != < <= > >=` and readable sugar (`is …`)
7. Boolean `and`
8. Boolean `or`

Example (explicit grouping recommended in teaching materials):
```rill
if (age >= 18 and has_id) or is_vip
    show "Allowed"
end
```

---

## 8. Control flow

### 8.1 Conditionals
```rill
if temperature > 80
    show "Hot"
otherwise if temperature > 60
    show "Nice"
otherwise
    show "Cold"
end
```

### 8.2 Loops

Counted loop:
```rill
repeat 10 times
    show "Hi"
end
```

While loop:
```rill
repeat while coins < 100
    change coins to coins + 1
end
```

For-each loop:
```rill
for each name in names
    show name
end
```

Range loop:
```rill
repeat for i from 1 to n
    show i
end
```

Range rules:
- `from A to B` is **inclusive** of `B`.
- Optional step: `repeat for i from 0 to 10 step 2`
- Exclusive end uses `until`:
- If `A > B` and no `step` is provided, this is an **error** with guidance (use `step -1` for countdown).
- If `step` is provided, its sign must match the direction (`step < 0` for descending, `step > 0` for ascending).
  - `repeat for i from 0 until n` runs `i = 0..n-1`

### 8.3 Early exit
- `stop` ends the nearest loop
- `skip` jumps to the next iteration

---

## 9. Input and conversions

### 9.1 Console input (`ask`)
- `ask` returns `text`.
- `ask` may take an inline prompt:

```rill
set name to ask "What is your name?"
```

### 9.2 Conversions
Canonical form is `TYPE from VALUE`:

```rill
set n to number from ask "Enter a number:"
set s to text from 123
```

Conversion failures are errors with guidance.

---

## 10. Collections, indexing, and mutation

### 10.1 List indexing is 0-based
```rill
set names to ["Ava", "Ben", "Cam"]
show names[0]  # "Ava"
```

Guardrails:
- Out-of-range access errors include list length and valid index range.

### 10.2 Convenience accessors (v1)
- `first of LIST`
- `last of LIST`
- `count of LIST`

### 10.3 Mutation of collections (**allowed in v1**)
Rill allows in-place mutation via `change` for common beginner workflows.

List element assignment:
```rill
set names to ["Ava", "Ben"]
change names[0] to "Alice"
```

Record field assignment:
```rill
set person to {name: "Ava", age: 12}
change person.age to 13
```

Map entry assignment:
```rill
set settings to {"theme": "dark"}
change settings["theme"] to "light"
```

Errors:
- Changing a list index out of range is an error (no auto-growing in v1).
- Changing a missing record field is an error with “did you mean” suggestions.
- Changing a missing map key creates the key **only if** the key is explicit (no implicit coercion).

---

## 11. Records and maps

### 11.1 Records (structured fields)
```rill
set person to {name: "Ava", age: 12}
show person.name
```

### 11.2 Maps (arbitrary keys)
```rill
set settings to {"theme": "dark", "retry": 3}
show settings["theme"]
```

---

## 12. Tables (first-class data feature)

### 12.1 Table creation
```rill
set people to table [
    {name: "Ava", age: 12},
    {name: "Ben", age: 14},
    {name: "Cam", age: 13}
]
```

### 12.2 Table operators (syntactically special)
Rill treats the following as **infix table operators** (left operand must be a `table`):

- `<table> where <expression>`
- `<table> select <field list>`
- `<table> group by <field list> <aggregate> [<field>]`

In v1, these operators apply **only to tables** (not lists).

### 12.3 Aggregates (v1)
Supported aggregates:
- `count` (no field required; counts rows)
- `sum <field>`
- `average <field>`
- `min <field>`
- `max <field>`

Examples:
```rill
show orders group by category count
show orders group by category sum price
show scores group by student average score
show readings group by sensor max value
```

---

## 13. Functions

### 13.1 Definition and return
```rill
define add taking a, b
    give back a + b
end
```

### 13.2 Defaults and named arguments
```rill
define greet taking name, punctuation = "!"
    give back "Hello, " + name + punctuation
end

show greet(name: "John", punctuation: "!!!")
```

### 13.3 Implicit return
If a function ends without `give back`, it returns `empty`.

### 13.4 Nested function definitions (v1)
- Not allowed in v1.

---

## 14. Imports (standard library usage)

Explicit imports:
```rill
use math
set x to math.round(3.7)
```

Initial v1 modules:
- `math`, `text`, `time`, `list`, `table`, `file`

---

## 15. Files (safe, explicit)

### 15.1 Save
```rill
use file

file.save "Remember milk" to "notes.txt"
file.save people to "people.csv"
```

Format resolution rules (v1):
- If the file extension is recognized for the value type, Rill uses it.
- Otherwise, specify a format:
```rill
file.save people to "people.data" as "csv"
```

### 15.2 Load
```rill
use file

set content to file.load text from "notes.txt"
set people2 to file.load table from "people.csv"
```

---

## 16. Errors that teach

### 16.1 Error format
Runtime errors include:
- Plain-language summary
- Exact line + snippet
- Likely cause
- 1–3 concrete fix suggestions

### 16.2 Example error (mock)
Given:
```rill
change totla to total + 1
```

Rill might report:
- **Error:** Cannot `change` `totla` because it does not exist.
- **Did you mean:** `total`?
- **Fix:** Create it first (`set total to 0`) or correct the spelling.

---

## 17. Built-in testing

### 17.1 Checks
```rill
check "add works"
    expect add(2, 3) equals 5
    expect add(-1, 1) equals 0
end
```

### 17.2 Matchers (v1)
Closed matcher set:
- `equals`
- `is greater than`
- `is at least`
- `is less than`
- `is at most`
- `contains` (for text and lists)
- `is empty` / `is not empty`

---

## 18. Optional keyword accessors (stylistic bridge)

Rill keeps standard operator access (`[]`, `.field`) because these are transferable. For teaching materials, v1 also permits two optional keyword forms:

- `item INDEX of LIST`  → `LIST[INDEX]`
- `field NAME of RECORD` → `RECORD.NAME`

Examples:
```rill
show item 0 of names
show field age of person
```

These are optional; the operator forms remain canonical in the language reference.

---

## 19. Example programs

### 19.1 First program
```rill
show "Hello!"
```

### 19.2 Sum numbers 1..N
```rill
set n to number from ask "Enter a number:"

set total to 0
repeat for i from 1 to n
    change total to total + i
end

show "Total is " + text from total
```

---

## 20. Why Rill (vs. “just use Python”)

- Language-native `trace` and `explain` modes.
- Two-verb assignment (`set` vs `change`) catches typos and accidental creation.
- Block scope prevents accidental variable leakage.
- First-class tables with readable operators and built-in aggregates.
- Teaching-grade error messages with concrete fixes.
- Built-in checks that lower the barrier to testing.
