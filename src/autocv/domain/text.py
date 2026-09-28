import re
import unicodedata

ESCAPES = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}", "–": "--", "—": "---", "“": "``", "”": "''",
    "‘": "`", "’": "'", "…": "...", "•": r"\textbullet{}", "\u00a0": " ",
}


LITERAL_UNICODE_PATTERN = re.compile(r"\\u([0-9A-Fa-f]{4})")


LATEX_ACCENT_PATTERN = re.compile(r'''\\([`'"^~=.])\{?([A-Za-z])\}?''')


LATEX_BRACED_ACCENT_PATTERN = re.compile(r"\\(c|v|u|H|k|r)\{([A-Za-z])\}")


LATEX_FORMAT_PATTERN = re.compile(
    r"\\(?:textit|textbf|emph|textrm|textsf|texttt|mathrm)\{([^{}]*)\}"
)


LATEX_ACCENTS = {
    "`": "\u0300", "'": "\u0301", "^": "\u0302", "~": "\u0303",
    "=": "\u0304", "u": "\u0306", ".": "\u0307", '"': "\u0308",
    "r": "\u030A", "H": "\u030B", "v": "\u030C", "c": "\u0327",
    "k": "\u0328",
}


LATEX_SPECIAL_LETTERS = {
    r"\ss{}": "ß", r"\ss": "ß", r"\ae{}": "æ", r"\ae": "æ",
    r"\AE{}": "Æ", r"\AE": "Æ", r"\oe{}": "œ", r"\oe": "œ",
    r"\OE{}": "Œ", r"\OE": "Œ", r"\o{}": "ø", r"\o": "ø",
    r"\O{}": "Ø", r"\O": "Ø", r"\l{}": "ł", r"\l": "ł",
    r"\L{}": "Ł", r"\L": "Ł",
}


def _decode_latex_accent(match: re.Match[str]) -> str:
    return unicodedata.normalize("NFC", match.group(2) + LATEX_ACCENTS[match.group(1)])


LATEX_TYPOGRAPHY = {
    r"\textquotedblleft": "“",
    r"\textquotedblright": "”",
    r"\textquoteleft": "‘",
    r"\textquoteright": "’",
    r"\textquotesingle": "'",
    r"\textendash": "–",
    r"\textemdash": "—",
    r"\(": "(",
    r"\)": ")",
    r"\[": "[",
    r"\]": "]",
}


LATEX_LITERALS = {ESCAPES[char]: char for char in "%&$_#{}~^\\"}


LATEX_LITERAL_PATTERN = re.compile("|".join(re.escape(token) for token in LATEX_LITERALS))


def plain(value: str) -> str:
    """Decode only allowed literal escapes; render() escapes all text once again."""
    value = unicodedata.normalize("NFC", value)
    value = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    # Gemini sometimes returns presentational LaTeX despite being asked for plain
    # values. Convert the harmless typography commands back to characters before
    # escaping the value locally. Unknown commands remain inert literal text.
    value = LITERAL_UNICODE_PATTERN.sub(
        lambda match: chr(int(match.group(1), 16)), value
    )
    value = LATEX_ACCENT_PATTERN.sub(_decode_latex_accent, value)
    value = LATEX_BRACED_ACCENT_PATTERN.sub(_decode_latex_accent, value)
    for source, target in LATEX_SPECIAL_LETTERS.items():
        value = value.replace(source, target)
    while True:
        unwrapped = LATEX_FORMAT_PATTERN.sub(r"\1", value)
        if unwrapped == value:
            break
        value = unwrapped
    for source, target in LATEX_TYPOGRAPHY.items():
        value = value.replace(source, target)
    # TeX consumes separator whitespace after quote control words. Mirror that
    # behavior so commands such as ``\textquotedblleft Europe`` do not add a gap.
    value = re.sub(r"([“‘])\s+", r"\1", value)
    value = re.sub(r"\s+([”’])", r"\1", value)
    value = re.sub(r"\\(?=(?:--|–|—))", "", value)
    return LATEX_LITERAL_PATTERN.sub(lambda match: LATEX_LITERALS[match.group(0)], value)


def tex(text: str) -> str:
    return "".join(ESCAPES.get(char, char) for char in text)


def safe_url(value: str) -> str:
    return value if re.fullmatch(r"https?://[^\s{}\\]+", value.strip()) else ""


def safe_email(value: str) -> str:
    return value if re.fullmatch(r"[^@\s{}\\]+@[^@\s{}\\]+\.[^@\s{}\\]+", value.strip()) else ""
