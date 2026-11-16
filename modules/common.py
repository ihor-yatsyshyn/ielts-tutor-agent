import math
import re


def norm_text(s: str) -> str:
    s = (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s.lower()).strip()


def quote_in_text(quote: str, text: str) -> bool:
    q = norm_text(quote).strip(" .…\"'")
    return len(q) >= 4 and q in norm_text(text)


def round_ielts(x: float) -> float:
    """Офіційне округлення середнього: .25 -> .5, .75 -> наступне ціле."""
    whole = math.floor(x)
    frac = x - whole
    if frac < 0.25:
        return float(whole)
    if frac < 0.75:
        return whole + 0.5
    return float(whole + 1)


def snap_band(v) -> float | None:
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if not 0 <= v <= 9:
        return None
    return round(v * 2) / 2
