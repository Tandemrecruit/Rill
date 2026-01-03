from __future__ import annotations

from pathlib import Path

from rill.cli import main


def test_cli_tokens_and_parse(tmp_path: Path, capsys):
    program = "set x to 2 + 3 * 4\nshow x\n"
    path = (tmp_path / "prog.rill").resolve()
    path.write_text(program, encoding="utf-8")

    assert main(["tokens", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Token(" in out

    # Backward compatible form (defaults to tokens)
    assert main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "Token(" in out

    assert main(["parse", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Program" in out

    assert main(["run", str(path)]) == 0
    out = capsys.readouterr().out
    assert "14" in out