from __future__ import annotations


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    raw = " ".join(value.split()).strip()
    upper = raw.upper()
    if upper.startswith("FT "):
        raw = raw[3:].strip()
    elif upper.startswith("FT-"):
        raw = raw[3:].strip()
    if upper.endswith(" FW"):
        raw = raw[:-3].strip()
    if upper.endswith(" SEA"):
        raw = raw[:-4].strip()
    return raw


def normalize_key(value: str | None) -> str:
    return normalize_label(value).upper()


def fishtalk_stage_to_aquamind(stage_name: str | None) -> str | None:
    upper = (stage_name or "").upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC", "GREEN", "EYE")):
        return "Egg&Alevin"
    if "FRY" in upper:
        return "Fry"
    if "PARR" in upper:
        return "Parr"
    if "SMOLT" in upper and ("POST" in upper or "LARGE" in upper):
        return "Post-Smolt"
    if "SMOLT" in upper:
        return "Smolt"
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE", "BROODSTOCK")):
        return "Adult"
    return None


S24_HALL_STAGE_MAP = {
    "A HØLL": "Egg&Alevin",
    "B HØLL": "Fry",
    "C HØLL": "Parr",
    "D HØLL": "Parr",
    "E HØLL": "Smolt",
    "F HØLL": "Smolt",
    "G HØLL": "Post-Smolt",
    "H HØLL": "Post-Smolt",
    "I HØLL": "Post-Smolt",
    "J HØLL": "Post-Smolt",
}

S03_HALL_STAGE_MAP = {
    "KLEKING": "Egg&Alevin",
    "5 M HØLL": "Fry",
    "11 HØLL A": "Smolt",
    "11 HØLL B": "Smolt",
    "18 HØLL A": "Post-Smolt",
    "18 HØLL B": "Post-Smolt",
    "800 HØLL": "Parr",
    "900 HØLL": "Parr",
}

S08_HALL_STAGE_MAP = {
    "KLEKING": "Egg&Alevin",
    "STARTFÓÐRING": "Fry",
    "T-HØLL": "Post-Smolt",
}

S16_HALL_STAGE_MAP = {
    "A HØLL": "Egg&Alevin",
    "B HØLL": "Fry",
    "C HØLL": "Parr",
    "D HØLL": "Smolt",
    "E1 HØLL": "Post-Smolt",
    "E2 HØLL": "Post-Smolt",
    "KLEKIHØLL": "Egg&Alevin",
    "STARTFÓÐRINGSHØLL": "Fry",
}

S21_HALL_STAGE_MAP = {
    "5M": "Fry",
    "A": "Parr",
    "BA": "Parr",
    "BB": "Parr",
    "C": "Smolt",
    "D": "Smolt",
    "E": "Post-Smolt",
    "F": "Post-Smolt",
    "ROGN": "Egg&Alevin",
}

FW22_APPLECROSS_HALL_STAGE_MAP = {
    "A1": "Egg&Alevin",
    "A2": "Egg&Alevin",
    "B1": "Fry",
    "B2": "Fry",
    "C1": "Parr",
    "C2": "Parr",
    "D1": "Smolt",
    "D2": "Smolt",
    "E1": "Post-Smolt",
    "E2": "Post-Smolt",
}

HALL_STAGE_PRIORITY_SITES = {
    "S24 STROND",
    "S03 NORÐTOFTIR",
    "S08 GJÓGV",
    "S16 GLYVRADALUR",
    "S21 VIÐAREIÐI",
    "FW22 APPLECROSS",
}


def stage_from_hall(site: str | None, container_group: str | None) -> str | None:
    site_key = normalize_key(site)
    hall_key = normalize_key(container_group)
    if site_key == "S24 STROND" and hall_key in S24_HALL_STAGE_MAP:
        return S24_HALL_STAGE_MAP[hall_key]
    if site_key == "S03 NORÐTOFTIR" and hall_key in S03_HALL_STAGE_MAP:
        return S03_HALL_STAGE_MAP[hall_key]
    if site_key == "S08 GJÓGV" and hall_key in S08_HALL_STAGE_MAP:
        return S08_HALL_STAGE_MAP[hall_key]
    if site_key == "S16 GLYVRADALUR" and hall_key in S16_HALL_STAGE_MAP:
        return S16_HALL_STAGE_MAP[hall_key]
    if site_key == "S21 VIÐAREIÐI" and hall_key in S21_HALL_STAGE_MAP:
        return S21_HALL_STAGE_MAP[hall_key]
    if site_key == "FW22 APPLECROSS" and hall_key in FW22_APPLECROSS_HALL_STAGE_MAP:
        return FW22_APPLECROSS_HALL_STAGE_MAP[hall_key]
    return None


def is_priority_hall_site(site: str | None) -> bool:
    return normalize_key(site) in HALL_STAGE_PRIORITY_SITES


def canonicalize_stage_sequence(
    stage_names: list[str],
    *,
    site: str | None,
    container_group: str | None,
) -> tuple[list[str], list[str]]:
    hall_stage = stage_from_hall(site, container_group)
    if hall_stage and is_priority_hall_site(site):
        return [hall_stage], [hall_stage]

    fishtalk_tokens: list[str] = []
    aquamind_tokens: list[str] = []
    for stage_name in stage_names:
        if stage_name and stage_name not in fishtalk_tokens:
            fishtalk_tokens.append(stage_name)
        mapped_stage = fishtalk_stage_to_aquamind(stage_name)
        if mapped_stage and mapped_stage not in aquamind_tokens:
            aquamind_tokens.append(mapped_stage)
    return fishtalk_tokens, aquamind_tokens
