"""All utskrift till terminalen går genom den här modulen; ingen annan modul i paketet anropar print.

Texten är exakt som förut, så Adrians facit är oförändrat. Färg kommer hit i 1.1.0, bara i en riktig terminal.
"""


def say(text=""):
    """Skriv en rad precis som den är."""
    print(text)


def error(text):
    """Felrad: Fel: <text>."""
    say(f"Fel: {text}")


def warn(text):
    """Varningsrad: Varning: <text>."""
    say(f"Varning: {text}")

def ask(prompt):
    """Läs en rad efter prompten (input skriver prompten)."""
    return input(prompt)


def fmt(x):
    """Ett tal i utskriften, som f"{x:g}" (högst sex värdesiffror). Ett ställe att ändra talformatet på."""
    return f"{x:g}"


def progress(items, text):
    """Går igenom items. Förloppsraden i terminalen (med texten text) kommer med rich i 1.1.1; här bara items."""
    return items
