"""Strukturen i kommandoregistret, help KOMMANDO och tools/gen_kommandon.py."""

import importlib.util
from pathlib import Path

import pytest

from spectrometer import commands, registry, session

ROT = Path(__file__).resolve().parents[1]


def gen_kommandon():
    """Läser in tools/gen_kommandon.py (tools är ingen paketmapp)."""
    spec = importlib.util.spec_from_file_location("gen_kommandon", ROT / "tools" / "gen_kommandon.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def all_commands():
    """Varje kommando som märkts med @registry.command i kommandomodulerna, i ordning."""
    found = []
    for module in commands.modules():
        for obj in vars(module).values():
            if hasattr(obj, "spektro_command"):
                found.append(obj)
    return found


def run_help(capsys, line):
    """Kör en rad i en ny state och ger raderna som skrevs."""
    registry.run_command(session.new_state(session.DEFAULTS), line)
    return capsys.readouterr().out.splitlines()


def test_help_names_are_unique_and_match_functions():
    funcs = all_commands()
    names = [f.spektro_command.name for f in funcs]
    assert len(names) == len(set(names))
    for func in funcs:
        assert func.__name__ == f"cmd_{func.spektro_command.name.replace(' ', '_')}"


def test_help_texts_are_one_clean_line():
    for func in all_commands():
        cmd = func.spektro_command
        assert cmd.text == cmd.text.strip(), cmd.name
        assert "\n" not in cmd.text, cmd.name
        assert "\n" not in cmd.usage, cmd.name


def test_help_prints_one_line_per_command(capsys):
    lines = run_help(capsys, "help")
    assert len(lines) == len(registry.COMMANDS)
    assert all(line.startswith(name + " ") for line, name in zip(lines, registry.COMMANDS, strict=True))


def test_help_command_shows_usage(capsys):
    roi = registry.COMMANDS["roi"]
    assert run_help(capsys, "help roi") == [f"roi {roi.text}", "Användning: roi X Y W H eller roi full"]
    assert run_help(capsys, "help quit") == [f"quit {registry.COMMANDS['quit'].text}"]


def test_help_unknown_command_gives_the_usual_error():
    state = session.new_state(session.DEFAULTS)
    with pytest.raises(ValueError) as unknown:
        registry.run_command(state, "foo")
    with pytest.raises(ValueError) as helped:
        registry.run_command(state, "help foo")
    assert str(helped.value) == str(unknown.value)
    assert str(helped.value) == "input.invalid_argument: okänt kommando foo. Skriv help för en lista."
    with pytest.raises(ValueError, match="okänt kommando roi step"):
        registry.run_command(state, "help roi step")


def test_help_takes_two_word_names(capsys):
    save = registry.COMMANDS["history save"]
    assert save.usage
    assert run_help(capsys, "help history save") == [f"history save {save.text}", f"Användning: {save.usage}"]
    assert run_help(capsys, "help history") == registry.help_for("history")


def test_command_with_two_arguments_still_works():
    @registry.command("prov", "en text")
    def cmd_prov(state, args):
        """Ett kommando utan usage."""

    assert cmd_prov.spektro_command.usage == ""
    assert cmd_prov.spektro_command.text == "en text"


def test_gen_kommandon_has_one_row_per_command():
    gen = gen_kommandon()
    rows = gen.rows()
    assert [row[0] for row in rows] == list(registry.COMMANDS)
    text = gen.document(rows)
    assert text.count("\n| ") == len(registry.COMMANDS) + 1  # rubrikraden och en rad per kommando
    assert "roi X Y W H eller roi full" in text


def test_gen_kommandon_fills_between_markers_only():
    gen = gen_kommandon()
    text = f"före\n{gen.START}\ngammalt\n{gen.SLUT}\nefter\n"
    filled = gen.fill(text, "NYTT")
    assert filled == f"före\n{gen.START}\nNYTT\n{gen.SLUT}\nefter\n"
    assert gen.fill(filled, "NYTT") == filled
    assert gen.fill("inga markörer\n", "NYTT") is None
