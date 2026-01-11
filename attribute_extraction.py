"""Domain-specific attribute extraction utilities.

These helpers run lightweight regex and keyword searches on the Romanian
product name and description fields to derive structured attributes required
for analytics.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, Optional


VOLUME_PATTERN = re.compile(r"(\d{1,3})\s?(ml)\b", re.IGNORECASE)
LENGTH_PATTERN = re.compile(r"(\d{2,4})\s?(mm)\b", re.IGNORECASE)
GRIT_PATTERN = re.compile(r"\b(\d{2,3}/\d{2,3})\b")
SHADE_PATTERN = re.compile(r"(#[0-9a-fA-F]{2,4}|[A-Z]{1,2}\d{2,3})\b")
STRENGTH_PATTERN = re.compile(r"(\d{2,3})\s?%")

FINISH_KEYWORDS = [
    "mat",
    "matte",
    "gloss",
    "lucios",
    "glitter",
    "shimmer",
    "reflectiv",
]
CURING_KEYWORDS = [
    "uv/led",
    "uv led",
    "uv",
    "led",
]
LIQUID_TYPES = [
    "cleaner",
    "remover",
    "aceton",  # Matches both acetona and acetonă
    "slip solution",
    "degresant",
    "primer",
]
SCENT_KEYWORDS = [
    "lavanda",
    "lavandă",
    "capsuni",
    "căpșuni",
    "vanilie",
    "cocos",
    "trandafir",
]
MATERIAL_KEYWORDS = [
    "inox",
    "otel",
    "oțel",
    "carbon",
    "abs",
    "plastic",
]
SHAPE_KEYWORDS = [
    "oval",
    "banană",
    "banana",
    "drept",
    "straight",
    "half-moon",
    "semilună",
]
COLOR_KEYWORDS = [
    "alb",
    "negru",
    "rosu",
    "roșu",
    "roz",
    "nude",
    "albastru",
    "verde",
    "mov",
    "galben",
    "portocaliu",
    "auriu",
    "argintiu",
]
COLLECTION_PATTERN = re.compile(r"colect(ia|iei)\s+([\w-]{3,30}?)(?:\s+\d|\s*$)", re.IGNORECASE)


def _first_match(pattern: re.Pattern[str], text: str) -> Optional[str]:
    match = pattern.search(text)
    return match.group(1) if match else None


def _first_keyword(text: str, keywords: Iterable[str]) -> Optional[str]:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None


def extract_attributes(name: str, description: str | None = None) -> Dict[str, object]:
    """Return a dict of attr_* fields derived from provided text fields."""

    haystack = " ".join(filter(None, [name or "", description or ""]))
    haystack_lower = haystack.lower()
    attributes: Dict[str, object] = {}

    if volume := _first_match(VOLUME_PATTERN, haystack):
        attributes["attr_volume_ml"] = float(volume)

    if grit := _first_match(GRIT_PATTERN, haystack):
        attributes["attr_grit"] = grit

    if shade_match := SHADE_PATTERN.search(haystack):
        attributes["attr_shade_code"] = shade_match.group(0).upper()

    if finish := _first_keyword(haystack_lower, FINISH_KEYWORDS):
        attributes["attr_finish"] = finish

    if curing := _first_keyword(haystack_lower, CURING_KEYWORDS):
        attributes["attr_curing_type"] = curing.replace(" ", "").upper()

    if liquid_type := _first_keyword(haystack_lower, LIQUID_TYPES):
        attributes["attr_liquid_type"] = liquid_type

    if scent := _first_keyword(haystack_lower, SCENT_KEYWORDS):
        attributes["attr_scent"] = scent

    if strength := _first_match(STRENGTH_PATTERN, haystack):
        attributes["attr_strength_percent"] = float(strength)

    if length := _first_match(LENGTH_PATTERN, haystack):
        attributes["attr_length_mm"] = float(length)

    if material := _first_keyword(haystack_lower, MATERIAL_KEYWORDS):
        attributes["attr_material"] = material

    if shape := _first_keyword(haystack_lower, SHAPE_KEYWORDS):
        attributes["attr_shape"] = shape

    if color := _first_keyword(haystack_lower, COLOR_KEYWORDS):
        attributes["attr_color_name"] = color

    if collection_match := COLLECTION_PATTERN.search(haystack):
        attributes["attr_collection"] = collection_match.group(2).strip()

    return attributes
