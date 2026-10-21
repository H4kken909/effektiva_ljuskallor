"""Prompten tål versaler, korta alias och felstavade kommandon (1.1.5)."""

from spectrometer import registry, session


def run(line):
    """Kör raden och ger (svaret, felet som text eller None)."""
    try:
        return registry.run_command(session.new_state(session.DEFAULTS), line), None
    except ValueError as error:
        return None, str(error)


def test_versaler_och_alias(capsys):
    assert run("HELP") == (None, None)
    assert capsys.readouterr().out.startswith("Kommandona står i grupper.")
    assert run("?") == (None, None)
    capsys.readouterr()
    for line in ("q", "exit", "Quit"):
        assert run(line) == (True, None)
        assert capsys.readouterr().out == "Avslutar.\n"


def test_menade_du():
    assert run("refrence") == (None, "input.invalid_argument: okänt kommando refrence. Menade du reference? "
                                     "Skriv help för en lista.")
    assert run("foo") == (None, "input.invalid_argument: okänt kommando foo. Skriv help för en lista.")
