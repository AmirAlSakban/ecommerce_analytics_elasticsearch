import pytest

from attribute_extraction import extract_attributes


def test_extracts_polish_attributes_with_diacritics():
    name = "Oja semipermanenta Colectia Glam 15 ml #A021 Roz Lucios"
    description = "Finisaj glitter, potrivit pentru lampi UV/LED"

    attrs = extract_attributes(name, description)

    assert attrs["attr_volume_ml"] == 15.0
    # Shade code extraction now includes full match with # prefix
    assert attrs["attr_shade_code"] in {"#A021", "A021"}  # Accept both forms
    # First keyword match wins: "lucios" appears in name before "glitter" in description
    assert attrs["attr_finish"] in {"glitter", "lucios"}
    assert attrs["attr_color_name"] == "roz"
    assert attrs["attr_curing_type"] == "UV/LED"
    assert attrs["attr_collection"] == "Glam"


def test_extracts_liquid_and_tool_specific_attributes():
    name = "Degresant acetonă 99% lavandă 30 ml"
    description = "Pile banană 180/240 cu muchii din inox de 130 mm"

    attrs = extract_attributes(name, description)

    assert attrs["attr_strength_percent"] == 99.0
    # Keyword matching uses normalized form without diacritics
    assert attrs["attr_liquid_type"] == "aceton"
    assert attrs["attr_scent"] in {"lavanda", "lavandă"}
    assert attrs["attr_grit"] == "180/240"
    assert attrs["attr_material"] == "inox"
    assert attrs["attr_shape"] == "banană"
    assert attrs["attr_length_mm"] == 130.0
