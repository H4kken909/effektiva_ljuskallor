"""source, roi, channel, axis och frames, sist info, cameras, snap och image: källan och vilken del som mäts."""

from pathlib import Path

from spectrometer import calc, files, measure, out, registry, session, source

GROUP = "kalla"  # help.kalla visar modulens kommandon


@registry.command("source", "file PATH eller camera N", "source file PATH eller source camera N")
def cmd_source(state, args):
    """Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden."""
    before = state["settings"]["source"]
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
    kind, where = state["settings"]["source"]
    if " " in str(where):
        where = f'"{where}"'  # som man skulle skriva kommandot
    out.say(f"source {kind} {where}")
    after = state["settings"]["source"]
    profiles = state["dark"] is not None or state["response"] is not None or state["reference"] is not None
    if profiles and (after[0] != before[0] or (after[0] == "camera" and after[1] != before[1])):
        # Annan kamera eller fil mot kamera: mörker och referens mättes med den gamla källan. PRO-16.
        out.warn("källan ändrad, mörker och referens kan vara fel")


@registry.command("roi", "X Y W H i pixlar, eller full för hela bilden", "roi X Y W H eller roi full")
def cmd_roi(state, args):
    """Kommandot roi X Y W H eller roi full; en ROI som inte ryms i senaste bilden, eller inte lämnar plats åt background N, ger fel och den gamla står kvar."""
    if args == ["full"]:
        session.set_setting(state, "roi", None)
        out.say("roi full")
        return
    registry.need(args, ("x", "y", "width", "height"), "roi")
    new_roi = (registry.to_int("x", args[0], 0), registry.to_int("y", args[1], 0),
               registry.to_int("width", args[2], 1), registry.to_int("height", args[3], 1))
    if state["image"] is not None:
        cfg = state["settings"]
        calc.prepare(state["image"], new_roi, cfg["axis"], cfg["channel"])
        if state["background"] is not None:  # background N ska fortfarande rymmas, annars kommer felet först vid step
            calc.side_background(state["image"], new_roi, state["background"], cfg["channel"], cfg["axis"])
    else:
        out.say("ROI:n kontrolleras vid nästa mätning.")
    session.set_setting(state, "roi", new_roi)
    out.say("roi " + " ".join(str(n) for n in new_roi))


@registry.command("channel", "gray, sum, red, green eller blue", "channel gray, sum, red, green eller blue")
def cmd_channel(state, args):
    """Kommandot channel NAMN: färgkanal ur calc.CHANNELS."""
    registry.need(args, ("name",), "channel")
    if args[0] not in calc.CHANNELS:
        raise ValueError(f"input.invalid_argument: okänd kanal {args[0]}, välj {', '.join(calc.CHANNELS)}")
    session.set_setting(state, "channel", args[0])
    out.say(f"channel: {args[0]}")


@registry.command("axis", "horizontal eller vertical", "axis horizontal eller axis vertical")
def cmd_axis(state, args):
    """Kommandot axis RIKTNING: riktning ur session.AXES."""
    registry.need(args, ("name",), "axis")
    if args[0] not in session.AXES:
        raise ValueError(f"input.invalid_argument: okänd riktning {args[0]}, välj {', '.join(session.AXES)}")
    session.set_setting(state, "axis", args[0])
    out.say(f"axis: {args[0]}")


@registry.command("frames", "N: bilder per mätning", "frames N")
def cmd_frames(state, args):
    """Kommandot frames N: antalet bilder per mätning, från 1 till registry.MAX_FRAMES (1000)."""
    registry.need(args, ("N",), "frames")
    n = registry.to_frames(args[0])
    session.set_setting(state, "frames", n)
    out.say(f"frames: {n}")


@registry.command("info", "källan: storlek, format och kamerans reglage")
def cmd_info(state, args):
    """Kommandot info: öppnar källan, läser en bild, skriver vad källan och drivrutinen säger och stänger igen.

    Exponering och gain är drivrutinens egna tal utan enhet; de jämförs bara med sig själva (step varnar vid ändring).
    """
    registry.need(args, (), "info")
    image, camera = measure._with_source(state, lambda s: (source.read_frame(s), source.describe(s)))
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
    registry.at_most_one(args, "snap", "N")
    n = registry.to_frames(args[0]) if args else 1
    images = measure._with_source(state, lambda s: source.read_frames(s, n))
    for path in files.save_snaps(state["settings"]["output_dir"], images):
        out.say(f"Sparad: {path.as_posix()}")


@registry.command("image", "[FIL]: spara en bild ur källan med ROI:n inritad (utan FIL: bild-ÅÅÅÅMMDD-HHMMSS.png i output_dir)")
def cmd_image(state, args):
    """Kommandot image [FIL]: läser en bild och sparar en kopia med ROI:n som grön ram, för att se var ROI:n ligger.

    Utan FIL hamnar den i output_dir med tidsstämpel, som snap. En fil som finns skrivs aldrig över.
    Fel: ValueError med input.invalid_argument om FIL inte slutar på .png eller redan finns.
    """
    registry.at_most_one(args, "image", "FIL")
    if args and not args[0].lower().endswith(".png"):
        raise ValueError(f"input.invalid_argument: {args[0]}: filnamnet ska sluta på .png")
    if args and Path(args[0]).exists():
        raise ValueError(f"input.invalid_argument: {args[0]} finns redan, image skriver inte över")
    image = measure._with_source(state, source.read_frame)
    if args:
        files.save_png(args[0], image, state["settings"]["roi"])
        out.say(f"Sparad: {args[0]}")
        return
    path = files.save_framed_image(state["settings"]["output_dir"], image, state["settings"]["roi"])
    out.say(f"Sparad: {path.as_posix()}")
