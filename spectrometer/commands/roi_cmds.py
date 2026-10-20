"""roi show, roi auto, roi profile, roi band, roi move och axis detect: hjälp att ställa ROI:n ur senaste bilden."""

from spectrometer import files, out, registry, roi


def _image(state):
    """Senaste råbilden; fel om ingen bild finns än."""
    if state["image"] is None:
        raise ValueError("input.missing_data: Ingen bild än. Kör step först.")
    return state["image"]


def _band(state):
    """Profilen tvärs spektrumet och bandet i den; fel om bilden inte har något ljust band."""
    profile = roi.cross_profile(_image(state), state["settings"]["axis"], state["settings"]["channel"])
    band = roi.find_band(profile)
    if band is None:
        raise ValueError(f"input.missing_data: inget ljust band tvärs spektrumet (axis {state['settings']['axis']}). "
                         "Tänd lampan och kör step, eller prova axis detect.")
    return profile, band


def _set_roi(state, new_roi):
    """Sätter ROI:n genom kommandot roi: samma kontroller och samma rad som när du skriver roi X Y W H."""
    registry.COMMANDS["roi"].run(state, [str(v) for v in new_roi])


@registry.command("roi show", "spara senaste bilden med ROI-rutan som data/roi-ÅÅÅÅMMDD-HHMMSS.png")
def cmd_roi_show(state, args):
    """Kommandot roi show: kopia av senaste bilden med ROI-rutan och mättade pixlar i magenta; sökvägen skrivs."""
    registry.need(args, (), "roi show")
    image = _image(state)
    current = state["settings"]["roi"] or (0, 0, image.shape[1], image.shape[0])
    path = files.save_roi_image(state["settings"]["output_dir"], image, current)
    out.say(f"Sparad i {path.as_posix()}", "ok")


@registry.command("roi auto", "föreslå en ROI ur det ljusa bandet i senaste bilden (ändrar inget)")
def cmd_roi_auto(state, args):
    """Kommandot roi auto: skriver ett förslag; du godtar det genom att skriva raden."""
    registry.need(args, (), "roi auto")
    _profile, (start, length) = _band(state)
    suggestion = roi.band_roi(state["image"].shape, state["settings"]["axis"], start, length)
    out.say(f"Förslag: roi {' '.join(str(v) for v in suggestion)} (kör raden för att godta)", "info")


@registry.command("roi profile", "bandets mitt, bredd vid halva höjden och bakgrund i senaste bilden")
def cmd_roi_profile(state, args):
    """Kommandot roi profile: tre rader om bandet tvärs spektrumet (rader vid horizontal, kolumner vid vertical)."""
    registry.need(args, (), "roi profile")
    profile, (start, length) = _band(state)
    word, words = ("rad", "rader") if state["settings"]["axis"] == "horizontal" else ("kolumn", "kolumner")
    out.say(f"Bandets mitt: {word} {start + (length - 1) / 2:g}")
    out.say(f"Bredd vid halva höjden: {length} {words}")
    out.say(f"Bakgrund: {roi.background(profile):.1f} counts, topp: {profile.max():.1f}")


@registry.command("roi band", "START WIDTH: ROI längs hela spektrumet, WIDTH pixlar tvärs från START")
def cmd_roi_band(state, args):
    """Kommandot roi band START WIDTH: rader START till START+WIDTH vid horizontal, kolumner vid vertical."""
    registry.need(args, ("START", "WIDTH"), "roi band")
    start = registry.to_int("START", args[0], 0)
    width = registry.to_int("WIDTH", args[1], 1)
    _set_roi(state, roi.band_roi(_image(state).shape, state["settings"]["axis"], start, width))


@registry.command("roi move", "DX DY: flytta ROI:n så många pixlar (den gamla står kvar vid fel)")
def cmd_roi_move(state, args):
    """Kommandot roi move DX DY: flyttar ROI:n; kontrolleras mot senaste bilden som roi X Y W H."""
    registry.need(args, ("DX", "DY"), "roi move")
    dx = registry.to_int("DX", args[0], -100000)
    dy = registry.to_int("DY", args[1], -100000)
    current = state["settings"]["roi"]
    if current is None:
        raise ValueError("input.missing_data: ingen ROI att flytta (hela bilden). Sätt en med roi X Y W H först.")
    _set_roi(state, (current[0] + dx, current[1] + dy, current[2], current[3]))


@registry.command("axis detect", "föreslå riktning ur det ljusa bandet i senaste bilden (ändrar inget)")
def cmd_axis_detect(state, args):
    """Kommandot axis detect: vågrätt eller lodrätt band ur de ljusa pixlarnas rektangel; skriver ett förslag."""
    registry.need(args, (), "axis detect")
    found = roi.detect_axis(_image(state), state["settings"]["channel"])
    if found is None:
        raise ValueError("input.missing_data: inget ljust band i bilden. Tänd lampan och kör step igen.")
    axis, wide, high = found
    word = "vågrätt" if axis == "horizontal" else "lodrätt"
    out.say(f"Bandet verkar vara {word} ({wide} px brett, {high} px högt). Kör axis {axis}.", "info")
