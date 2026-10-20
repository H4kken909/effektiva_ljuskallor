"""help, quit och show."""

from spectrometer import out, registry


@registry.command("help", "Visa kommandona")
def cmd_help(state, args):
    """Kommandot help: en rad per kommando i registret."""
    registry.need(args, (), "help")
    for line in registry.help_lines():
        out.say(line)


@registry.command("quit", "Avsluta")
def cmd_quit(state, args):
    """Kommandot quit: skriver Avslutar. och ber main att avsluta (svarar True)."""
    registry.need(args, (), "quit")
    out.say("Avslutar.")
    return True


@registry.command("show", "Visa inställningarna")
def cmd_show(state, args):
    """Kommandot show: inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns."""
    registry.need(args, (), "show")
    for key, value in state["settings"].items():
        out.say(f"{key}: {value}")
    calibration = "ja" if state["coefficients"] is not None else "nej"
    dark = "ja" if state["dark"] is not None else "nej"
    response = "ja" if state["response"] is not None else "nej"
    reference = "ja" if state["reference"] is not None else "nej"
    use = "on" if state["use_response"] else "off"
    out.say(f"kalibrering: {calibration}")
    out.say(f"mörker: {dark}")
    out.say(f"respons: {response}, {use}")
    out.say(f"referens: {reference}")
    out.say(f"mode: {state['mode']}")
    out.say("Mätning: ja" if state["spectrum"] is not None else "Mätning: nej")