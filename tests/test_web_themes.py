from ilearn.web.themes import band_for_grade, load_theme_css, theme_key_for


def test_band_for_grade():
    assert band_for_grade(4) == "primary"
    assert band_for_grade(8) == "junior"
    assert band_for_grade(11) == "senior"


def test_band_for_grade_edges():
    assert band_for_grade(6) == "primary"
    assert band_for_grade(7) == "junior"


def test_theme_key():
    assert theme_key_for(5, "female") == "primary_female"


def test_theme_key_unknown_gender_falls_back_to_unspecified():
    assert theme_key_for(5, "other") == "primary_unspecified"


def test_load_theme_css_returns_css_with_accent():
    css = load_theme_css("primary_female")
    assert "--accent" in css


def test_load_theme_css_all_nine_keys():
    bands = ("primary", "junior", "senior")
    genders = ("male", "female", "unspecified")
    for band in bands:
        for gender in genders:
            css = load_theme_css(f"{band}_{gender}")
            assert "--accent" in css


def test_load_css_merges_base_styles_and_theme_pack():
    from ilearn.web.app import _load_css

    css = _load_css(grade=5, gender="female")
    assert "--ink:" in css
    assert ".brand-wrap" in css
    assert "--accent:" in css
    assert "#e84393" in css
