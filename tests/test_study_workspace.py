import pytest
from scripts.study_workspace import slugify

def test_slugify_basic():
    assert slugify("My Study 2026") == "my-study-2026"

def test_slugify_accents_nfkd():
    assert slugify("Attività Didàttica") == "attivita-didattica"

def test_slugify_collapses_punctuation():
    assert slugify("A///B   C!!!D") == "a-b-c-d"

def test_slugify_strips_leading_trailing_hyphens_dots_spaces():
    assert slugify("  .-.Hello.-.  ") == "hello"

def test_slugify_empty_raises():
    with pytest.raises(ValueError, match="empty_slug"):
        slugify("...---...")

def test_slugify_reserved_name_raises():
    for reserved in ["CON", "con", "PRN", "AUX", "NUL", "COM1", "LPT9"]:
        with pytest.raises(ValueError, match="reserved_name"):
            slugify(reserved)

def test_slugify_max_length_80():
    long_name = "a" * 200
    assert len(slugify(long_name)) == 80
