"""Text normalisation for business names and addresses.

Everything here is plain string processing with hand-written abbreviation
tables. No external data (registries, geocoders) is used, as required by the
challenge rules.

The same functions run on every source and every country. Nothing is keyed
on the country label, so the unseen test country (France) gets exactly the
same treatment as US and India.
"""
from __future__ import annotations

import re
import unicodedata

from unidecode import unidecode

# ---------------------------------------------------------------- shared --

_APOS = re.compile(r"['`’]")
_NAME_TOKEN = re.compile(r"[a-z0-9]+")
# keep compound house numbers such as 5-7-142/ep or 1/2 as one token
_ADDR_TOKEN = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*")
_ORDINAL = re.compile(r"^(\d+)(?:st|nd|rd|th)$")
_DIGIT = re.compile(r"\d")
_GLUE = re.compile(r"(\d)([a-z]{3,})")


def to_ascii(s: str) -> str:
    """NFKC, transliterate non-Latin scripts and accents to ASCII, lowercase."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    if not s.isascii():
        s = unidecode(s)
    return s.lower()


def _plural(tok: str) -> str:
    # services -> service, systems -> system; keep 'ss' endings (business, class)
    if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss") and not tok[-2].isdigit():
        return tok[:-1]
    return tok


# ------------------------------------------------------------------ names --

NAME_CANON = {
    "private": "pvt", "pvt": "pvt", "prvt": "pvt",
    "limited": "ltd", "ltd": "ltd", "ltda": "ltd",
    "incorporated": "inc", "inc": "inc",
    "corporation": "corp", "corp": "corp", "corpn": "corp",
    "company": "co", "co": "co", "cos": "co",
    "and": "and", "et": "and", "n": "and",
    "brothers": "bros", "bros": "bros", "bro": "bros",
    "international": "intl", "intl": "intl", "internationa": "intl",
    "enterprise": "ent", "enterprises": "ent", "entp": "ent", "ent": "ent",
    "industries": "ind", "industry": "ind", "inds": "ind",
    "technologies": "tech", "technology": "tech", "tech": "tech", "techno": "tech",
    "service": "service", "services": "service", "svc": "service", "svcs": "service", "srvc": "service",
    "solution": "solution", "solutions": "solution", "soln": "solution",
    "manufacturing": "mfg", "mfg": "mfg", "manufacturer": "mfg", "manufacturers": "mfg",
    "engineering": "engg", "engg": "engg", "eng": "engg",
    "associates": "assoc", "associate": "assoc", "assoc": "assoc", "asso": "assoc",
    "consultants": "consult", "consultant": "consult", "consultancy": "consult", "consulting": "consult",
    "pharmaceuticals": "pharma", "pharmaceutical": "pharma", "pharma": "pharma",
    "agencies": "agency", "agency": "agency",
    "department": "dept", "dept": "dept",
    "center": "centre", "centre": "centre", "ctr": "centre",
    "saint": "st", "sainte": "ste",
    "societe": "ste", "ste": "ste", "etablissements": "ets", "ets": "ets",
}

# legal forms, honorifics and filler: dropped from the "core" name used for
# blocking and token overlap, kept in the full name for fuzzy comparison
NAME_STOP = {
    "pvt", "ltd", "inc", "corp", "co", "llc", "llp", "lp", "plc", "pllc", "pc", "opc", "gmbh",
    "sarl", "sas", "sasu", "sa", "eurl", "sci", "snc", "scop", "selarl", "ste", "ets",
    "the", "of", "and", "a", "an", "les", "le", "la", "de", "du", "des",
    "mr", "mrs", "ms", "dr", "shri", "sri", "smt", "m/s", "messrs",
    "com", "www", "net", "org",
}

_DBA = re.compile(
    r"\b(?:trading as|t/a|d/b/a|dba|doing business as|also known as|aka|formerly known as|formerly|operating as|o/a)\b"
)


def name_variants(raw: str) -> list[str]:
    """Split 'X trading as Y' style names into [full, X, Y] (ASCII, lowercase)."""
    s = to_ascii(raw)
    parts = [p.strip(" ,.-") for p in _DBA.split(s)]
    parts = [p for p in parts if p]
    return [s] + parts if len(parts) > 1 else [s]


def name_tokens(text: str) -> list[str]:
    text = _APOS.sub("", text).replace("&", " and ").replace("m/s", " ")
    out = []
    for t in _NAME_TOKEN.findall(text):
        t = NAME_CANON.get(t, t)
        out.append(_plural(t))
    return out


# Phonetic skeleton for transliterated names. Indian-script names come out of
# transliteration as e.g. 'praaivett limittedd' for 'private limited'. Mapping
# sound-alike letters together and dropping vowels and doubled letters gives
# both spellings the same key ('prwt lmt'). Measured on 3,000 matched pairs
# whose Source 2/3 name was in an Indian script: the share with fuzzy
# similarity >= 80 rose from 29% (plain transliteration) to 90%.
_DIGRAPHS = [("ph", "f"), ("sh", "s"), ("ch", "c"), ("th", "t"), ("dh", "d"), ("kh", "k"),
             ("gh", "g"), ("bh", "b"), ("ck", "k"), ("x", "ks"), ("w", "v"), ("z", "s"),
             ("c", "s"), ("k", "s"), ("q", "s")]
_DEVOICE = str.maketrans("gdbjvzq", "ktpcwsk")
_VOWELS = set("aeiouy")
_REPEAT = re.compile(r"(.)\1+")


def phonetic_key(word: str) -> str:
    for a, b in _DIGRAPHS:
        word = word.replace(a, b)
    word = word.translate(_DEVOICE)
    if not word:
        return word
    sk = word[0] + "".join(ch for ch in word[1:] if ch not in _VOWELS)
    return _REPEAT.sub(r"\1", sk)


def phonetic_tokens(ascii_text: str) -> list[str]:
    text = _APOS.sub("", ascii_text).replace("&", " ")
    return [phonetic_key(t) for t in _NAME_TOKEN.findall(text) if not t.isdigit()]


# Only long legal words: short skeletons collide with real words (the key
# of 'sri' is 'sr', the same as 'care'; 'plc' gives 'pls', the same as 'palace').
_LEGAL_WORDS = ["private", "pvt", "limited", "company", "corporation", "incorporated"]
PHON_STOP = {phonetic_key(w) for w in _LEGAL_WORDS} - {""}


def normalize_name(raw: str) -> dict:
    variants = name_variants(raw)
    parts = variants[1:] if len(variants) > 1 else variants
    full_tokens = name_tokens(" ".join(parts))
    core = [t for t in full_tokens if t not in NAME_STOP and len(t) > 1]
    # core of each DBA part, so 'X trading as Y' can match either X or Y
    alt = [" ".join(t for t in name_tokens(v) if t not in NAME_STOP and len(t) > 1) for v in variants[1:]]
    ascii_name = " ".join(parts)
    phon = [t for t in phonetic_tokens(ascii_name) if t not in PHON_STOP]
    return {
        "name_norm": " ".join(full_tokens),
        "name_core": " ".join(core) if core else " ".join(full_tokens),
        "name_alt": "|".join(a for a in alt if a),
        "name_phon": " ".join(phon) if phon else " ".join(phonetic_tokens(ascii_name)),
    }


# -------------------------------------------------------------- addresses --

ADDR_CANON = {
    # street types (US + India + France)
    "street": "st", "str": "st", "st": "st",
    "road": "rd", "rd": "rd",
    "avenue": "ave", "ave": "ave", "av": "ave", "aven": "ave",
    "drive": "dr", "dr": "dr", "drv": "dr",
    "lane": "ln", "ln": "ln",
    "boulevard": "blvd", "blvd": "blvd", "bd": "blvd", "boul": "blvd",
    "circle": "cir", "cir": "cir", "circ": "cir",
    "court": "ct", "ct": "ct",
    "place": "pl", "pl": "pl",
    "terrace": "ter", "ter": "ter", "terr": "ter",
    "parkway": "pkwy", "pkwy": "pkwy",
    "highway": "hwy", "hwy": "hwy",
    "square": "sq", "sq": "sq",
    "trail": "trl", "trl": "trl",
    "way": "way", "wy": "way",
    "point": "pt", "pt": "pt",
    "mount": "mt", "mt": "mt",
    "fort": "ft", "ft": "ft",
    "route": "rte", "rte": "rte",
    "chemin": "ch", "ch": "ch",
    "impasse": "imp", "imp": "imp",
    "allee": "all",
    "faubourg": "fbg", "fbg": "fbg",
    "saint": "st", "sainte": "ste",
    "marg": "marg", "mg": "marg",
    "nagar": "nagar", "ngr": "nagar",
    "colony": "colony", "col": "colony",
    "sector": "sector", "sec": "sector",
    "near": "near", "nr": "near", "opposite": "opp", "opp": "opp", "behind": "behind", "bhd": "behind",
    # units
    "suite": "ste", "ste": "ste", "apartment": "apt", "apt": "apt", "unit": "unit",
    "building": "bldg", "bldg": "bldg", "floor": "fl", "fl": "fl", "flr": "fl",
    # directions
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
}

# tokens that carry no location information
ADDR_STOP = {"no", "number", "num", "plot", "house", "h", "door", "d", "flat", "null", "none", "nan",
             "city", "district", "dist", "the", "of", "and", "de", "du", "des", "la", "le", "les"}

US_STATES = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca", "colorado": "co",
    "connecticut": "ct", "delaware": "de", "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
    "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks", "kentucky": "ky", "louisiana": "la",
    "maine": "me", "maryland": "md", "massachusetts": "ma", "michigan": "mi", "minnesota": "mn",
    "mississippi": "ms", "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
    "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny", "north carolina": "nc",
    "north dakota": "nd", "ohio": "oh", "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa",
    "rhode island": "ri", "south carolina": "sc", "south dakota": "sd", "tennessee": "tn", "texas": "tx",
    "utah": "ut", "vermont": "vt", "virginia": "va", "washington": "wa", "west virginia": "wv",
    "wisconsin": "wi", "wyoming": "wy", "district of columbia": "dc",
}
IN_STATES = {
    "andhra pradesh": "ap", "arunachal pradesh": "ar", "assam": "as", "bihar": "br", "chhattisgarh": "cg",
    "goa": "ga", "gujarat": "gj", "haryana": "hr", "himachal pradesh": "hp", "jharkhand": "jh",
    "karnataka": "ka", "kerala": "kl", "madhya pradesh": "mp", "maharashtra": "mh", "manipur": "mn",
    "meghalaya": "ml", "mizoram": "mz", "nagaland": "nl", "odisha": "od", "orissa": "od", "punjab": "pb",
    "rajasthan": "rj", "sikkim": "sk", "tamil nadu": "tn", "telangana": "tg", "tripura": "tr",
    "uttar pradesh": "up", "uttarakhand": "uk", "west bengal": "wb", "delhi": "dl", "new delhi": "dl",
    "jammu and kashmir": "jk", "ladakh": "la", "puducherry": "py", "pondicherry": "py", "chandigarh": "ch",
    "andaman and nicobar islands": "an", "lakshadweep": "ld",
}
_STATE_CODES = {**US_STATES, **IN_STATES}
# longest names first so 'west virginia' wins over 'virginia'
_STATE_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _STATE_CODES), key=len, reverse=True)) + r")\b")
_STATE_ALIASES = {"ts": "tg", "ct": "cg", "or": "od", "ut": "uk"}  # alternative Indian codes, see note below


def normalize_address(raw: str) -> dict:
    s = to_ascii(raw)
    s = _APOS.sub("", s).replace("&", " and ").replace("#", " ")
    s = _STATE_RE.sub(lambda m: " " + _STATE_CODES[m.group(1)] + " ", s)
    s = _GLUE.sub(r"\1 \2", s)
    raw_tokens = []
    for t in _ADDR_TOKEN.findall(s):
        parts = re.split(r"[-/]", t)
        if len(parts) > 1 and any(p.isalpha() and len(p) >= 3 for p in parts):
            raw_tokens.extend(p for p in parts if p)
        else:
            raw_tokens.append(t)
    toks, nums = [], []
    for t in raw_tokens:
        m = _ORDINAL.match(t)
        if m:
            t = m.group(1)
        t = ADDR_CANON.get(t, t)
        if t in ADDR_STOP:
            continue
        if _DIGIT.search(t):
            nums.append(t)
        toks.append(t)
    return {
        "addr_norm": " ".join(toks),
        "addr_words": " ".join(t for t in toks if not _DIGIT.search(t)),
        "addr_nums": " ".join(nums),
        "house_no": nums[0] if nums else "",
    }


# Note on _STATE_ALIASES: it is not applied inside normalize_address because
# two-letter tokens such as 'or' and 'ct' are also ordinary words/street types.
# Code that compares state tokens can map them through it.


def normalize_record(name: str, address: str) -> dict:
    return {**normalize_name(name), **normalize_address(address)}


if __name__ == "__main__":
    cases = [
        ("Nexjaxlyra trading as Indian Care Private Limited", "Itwari Mohalla Shahdol, Shahdol, Madhya Pradesh"),
        ("इंडियन केयर प्राइवेट लिमिटेड", "#917/8 Itwari Mohalla Shahdol, Shahdol, Umaria, MP"),
        ("Montari Spíre", "#34184 Tanglewood Pass, SAN TAN Valley CITY, Arizona"),
        ("Zasoft, Co", "295 10RD CIR, NORTH BEND, WA"),
        ("IMY India Co", "PLOT 0578 5-7-142/EP, SRIPURAM COLONY, CHENGICHARLA, AMBERPET, తెలంగాణ"),
        ("Orelee's Barbershop", "1795 Westchester Drive, High Point, NC"),
        ("Boulangerie Dupont & Fils SARL", "12 bis Rue de la République, 69002 Lyon"),
    ]
    for n, a in cases:
        print(normalize_record(n, a))
