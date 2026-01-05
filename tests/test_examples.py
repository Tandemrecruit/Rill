from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _norm(s: str) -> str:
    # normalize Windows newlines and strip trailing whitespace-only lines
    s = s.replace("\r\n", "\n")
    return "\n".join([line.rstrip() for line in s.split("\n")]).strip() + "\n"


def test_examples_match_expected_output() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples"

    # If you haven't added examples yet, fail with a helpful message.
    assert examples_dir.exists(), "Missing examples/ directory. Add examples/*.rill and *.out files."

    rill_files = sorted(examples_dir.glob("*.rill"))
    assert rill_files, "No .rill files found in examples/"

    for program in rill_files:
        expected_file = program.with_suffix(".out")
        assert expected_file.exists(), f"Missing expected output file: {expected_file.name}"

        expected = _norm(expected_file.read_text(encoding="utf-8-sig"))
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "rill", "run", str(program)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise AssertionError(f"{program.name} timed out after 30 seconds")

        assert proc.returncode == 0, (
            f"{program.name} failed\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}\n"
        )

        actual = _norm(proc.stdout)
        assert actual == expected, (
            f"{program.name} output mismatch\n"
            f"--- expected ({expected_file.name}) ---\n{expected}"
            f"--- actual ---\n{actual}"
        )
