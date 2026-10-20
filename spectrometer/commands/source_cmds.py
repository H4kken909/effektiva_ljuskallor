"""source, roi, channel, axis och frames: var bilden kommer ifrån och vilken del som mäts."""

from spectrometer import calc, out, registry, session


@registry.command("source", "file PATH eller camera N")
def cmd_source(state, args):
    """Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden."""
    if not args:
        raise ValueError("input.invalid_argument: source: kind saknas")
    if args[0] == "file":
        registry.need(args, ("kind", "path"), "source")
        session.set_setting(state, "source", ("file", args[1]))
    elif args[0] == "camera":
        registry.need(args, ("kind", "index"), "source")
        index = registry.to_int("index", args[1], 0)
        session.set_setting(state, "source", ("camera", index))
    else:
        raise ValueError(f"input.invalid_argument: okänd källa {args[0]}, välj file eller camera")
    state["image"] = None
    out.say(f"source: {state['settings']['source']}")


@registry.command("roi", "X Y W H i pixlar, eller full för hela bilden")
def cmd_roi(state, args):
    """Kommandot roi X Y W H eller roi full; en ROI som inte ryms i senaste bilden ger fel och den gamla står kvar."""
    if args == ["full"]:
        session.set_setting(state, "roi", None)
        out.say("roi: None (hela bilden)")
        return
    registry.need(args, ("x", "y", "width", "height"), "roi")
    x = registry.to_int("x", args[0], 0)
    y = registry.to_int("y", args[1], 0)
    width = registry.to_int("width", args[2], 1)
    height = registry.to_int("height", args[3], 1)
    new_roi = (x, y, width, height)
    if state["image"] is not None:
        calc.prepare(state["image"], new_roi, state["settings"]["axis"], state["settings"]["channel"])
    else:
        out.say("ROI:n kontrolleras vid nästa mätning.")
    session.set_setting(state, "roi", new_roi)
    out.say(f"roi: {new_roi}")


@registry.command("channel", "gray, sum, red, green eller blue")
def cmd_channel(state, args):
    """Kommandot channel NAMN: färgkanal ur calc.CHANNELS."""
    registry.need(args, ("name",), "channel")
    if args[0] not in calc.CHANNELS:
        raise ValueError(f"input.invalid_argument: okänd kanal {args[0]}, välj {', '.join(calc.CHANNELS)}")
    session.set_setting(state, "channel", args[0])
    out.say(f"channel: {args[0]}")


@registry.command("axis", "horizontal eller vertical")
def cmd_axis(state, args):
    """Kommandot axis RIKTNING: riktning ur session.AXES."""
    registry.need(args, ("name",), "axis")
    if args[0] not in session.AXES:
        raise ValueError(f"input.invalid_argument: okänd riktning {args[0]}, välj {', '.join(session.AXES)}")
    session.set_setting(state, "axis", args[0])
    out.say(f"axis: {args[0]}")


@registry.command("frames", "N: bilder per mätning")
def cmd_frames(state, args):
    """Kommandot frames N: antalet bilder per mätning, minst 1."""
    registry.need(args, ("N",), "frames")
    n = registry.to_int("N", args[0], 1)
    session.set_setting(state, "frames", n)
    out.say(f"frames: {n}")
