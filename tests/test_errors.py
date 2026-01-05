from __future__ import annotations

from pathlib import Path

from rill.cli import main


def test_cli_formats_lex_error(tmp_path: Path, capsys) -> None:
    path = (tmp_path / "bad.rill").resolve()
    path.write_text("$\n", encoding="utf-8", newline="\n")

    assert main(["tokens", str(path)]) == 1
    captured = capsys.readouterr()
    err = captured.err

    assert "RillLexError" in err
    assert "Unexpected character" in err
    assert "$" in err
    assert "^" in err


def test_cli_formats_runtime_error(tmp_path: Path, capsys) -> None:
    path = (tmp_path / "bad.rill").resolve()
    path.write_text("stop\n", encoding="utf-8", newline="\n")

    assert main(["run", str(path)]) == 1
    captured = capsys.readouterr()
    err = captured.err

    assert "RillRuntimeError" in err
    assert "stop" in err
    assert "^" in err
