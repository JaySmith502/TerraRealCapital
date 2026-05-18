from trc.narrative import split_sections, section_titles, splice_section

MD = "Intro line\n\n## Alpha\n\nA body\n\n## Beta\n\nB body\n"

def test_split_keeps_preamble_and_sections():
    pre, secs = split_sections(MD)
    assert pre.strip() == "Intro line"
    assert [s.title for s in secs] == ["Alpha", "Beta"]
    assert secs[0].body.strip() == "A body"

def test_titles_helper():
    assert section_titles(MD) == ["Alpha", "Beta"]

def test_splice_replaces_only_target_section():
    out = splice_section(MD, "Beta", "NEW B")
    assert "## Beta\n\nNEW B" in out
    assert "A body" in out          # other section untouched
    assert out.count("## ") == 2

def test_splice_unknown_title_raises():
    import pytest
    with pytest.raises(KeyError):
        splice_section(MD, "Gamma", "x")
