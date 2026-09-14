"""Unit tests for the typo-tolerant text normalizer."""

from robex.ai.normalizer import TextNormalizer


def test_typo_correction_basic():
    normalizer = TextNormalizer()
    assert normalizer.normalize("clck gern botton") == "click green button"


def test_typo_correction_preserves_correct_words():
    normalizer = TextNormalizer()
    assert normalizer.normalize("click the green button") == "click the green button"


def test_does_not_mangle_unrelated_lookalike_words():
    normalizer = TextNormalizer()
    # "double" must not get corrected to "blue" just because the strings are similar.
    assert normalizer.normalize("double jump") == "double jump"


def test_filler_removal():
    normalizer = TextNormalizer()
    assert normalizer.normalize("please could you click the button now") == "click the button"
    assert normalizer.normalize("um jump") == "jump"


def test_synonym_mapping():
    normalizer = TextNormalizer()
    assert normalizer.normalize("tap shift") == "press shift"
    assert normalizer.normalize("walk for 3 seconds") == "hold w for 3 seconds"


def test_multiline_paragraph_segmentation():
    normalizer = TextNormalizer()
    text = "click green button\nwait 2 seconds\njump"
    assert normalizer.normalize(text) == "click green button; wait 2 seconds; jump"


def test_sentence_period_segmentation_without_breaking_decimals():
    normalizer = TextNormalizer()
    text = "click green button. wait 1.5 seconds. jump"
    assert normalizer.normalize(text) == "click green button; wait 1.5 seconds; jump"


def test_empty_and_whitespace_input():
    normalizer = TextNormalizer()
    assert normalizer.normalize("") == ""
    assert normalizer.normalize("   \n\t  ") == ""
