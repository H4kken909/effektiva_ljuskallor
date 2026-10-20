"""source, roi, channel, axis och frames: var bilden kommer ifrån och vilken del som mäts. Sist kommandon som tittar på källan."""

from spectrometer import calc, files, measure, out, registry, session, source


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


@registry.command("info", "källan: storlek, format och kamerans reglage")
def cmd_info(state, args):
    """Kommandot info: öppnar källan, läser en bild, skriver vad källan och drivrutinen säger och stänger igen.

    Exponering och gain är drivrutinens egna tal utan enhet; de jämförs bara med sig själva (step varnar vid ändring).
    """
    registry.need(args, (), "info")
    image, camera = measure._with_source(state, None, lambda s: (source.read_frame(s), source.describe(s)))
    height, width = image.shape[:2]
    kind, value = state["settings"]["source"]
    if kind != "camera":
        out.say(f"Källa: fil {value}, {width}x{height}")
        return
    backend = camera["backend"] or "okänd"  # None när drivrutinen inte säger något
    fourcc = camera["fourcc"] or "okänd"
    out.say(f"Källa: kamera {value} ({backend}), {width}x{height}, {fourcc}")
    out.say(f"exponering: {camera['exposure']:g}, gain: {camera['gain']:g}, auto-exponering: "
            f"{camera['auto_exposure']:g}, bildtakt: {camera['fps']:g} (enligt drivrutinen)")
    if camera["fourcc"] == "MJPG":
        out.warn("MJPG: JPEG-komprimeringen ändrar pixelvärdena. Välj YUYV om kameran klarar det.")


@registry.command("cameras", "prova kamera 0 till 4 och skriv vilka som ger bild")
def cmd_cameras(state, args):
    """Kommandot cameras: provar kameranummer 0 till 4 med source.probe och skriver en rad per nummer. Källan ändras inte."""
    registry.need(args, (), "cameras")
    max_index = 4
    found = {index: (width, height) for index, width, height in source.probe(max_index)}
    for index in range(max_index + 1):
        size = found.get(index)
        out.say(f"kamera {index}: {size[0]}x{size[1]}" if size else f"kamera {index}: ingen bild")


@registry.command("snap", "[N]: spara N råbilder (1) ur källan som PNG i output_dir, utan att mäta")
def cmd_snap(state, args):
    """Kommandot snap [N]: läser N bilder ur källan och sparar dem som PNG; state ändras inte."""
    if len(args) > 1:
        raise ValueError("input.invalid_argument: snap tar högst ett ord (N)")
    n = registry.to_int("N", args[0], 1) if args else 1
    images = measure._with_source(state, None, lambda s: source.read_frames(s, n))
    for path in files.save_snaps(state["settings"]["output_dir"], images):
        out.say(f"Sparad: {path.as_posix()}")


@registry.command("image", "[FIL]: spara en bild ur källan med ROI:n inritad (bild.png)")
def cmd_image(state, args):
    """Kommandot image [FIL]: läser en bild och sparar en kopia med ROI:n som grön ram, för att se var ROI:n ligger."""
    if len(args) > 1:
        raise ValueError("input.invalid_argument: image tar högst ett ord (FIL)")
    path = args[0] if args else "bild.png"
    if not path.lower().endswith(".png"):
        raise ValueError(f"input.invalid_argument: {path}: filnamnet ska sluta på .png")
    image = measure._with_source(state, None, source.read_frame)
    files.save_png(path, image, state["settings"]["roi"])
    out.say(f"Sparad: {path}")
