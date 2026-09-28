import re

import pytest
from autocv.domain.profile import CandidateProfile, missing_for_generation
from autocv.domain.profile_markdown import date_range, month_label, render_profile_markdown
from pydantic import ValidationError


def test_empty_profile_is_valid_but_incomplete():
    assert missing_for_generation(CandidateProfile()) == ["name", "email", "experience_or_education"]


def test_education_alone_satisfies_the_content_requirement():
    profile = CandidateProfile(first_name="A", email="a@b.co",
                               education=[{"institution": "U", "degree": "D"}])
    assert missing_for_generation(profile) == []


def test_strings_are_stripped_and_line_endings_normalized():
    profile = CandidateProfile(first_name="  Ana  ", summary="a\r\nb")
    assert profile.first_name == "Ana" and profile.summary == "a\nb"


def test_end_date_may_never_be_omitted_silently_for_a_job():
    with pytest.raises(ValidationError):
        CandidateProfile(experience=[{"company": "A", "title": "B", "start_date": "2024-01"}])


@pytest.mark.parametrize("start,end,current,expected", [
    ("2024-10", None, True, "Oct 2024 – Present"),
    ("2022-06", "2022-12", False, "Jun 2022 – Dec 2022"),
    ("2023-05", None, False, "May 2023"),
    (None, "2023-05", False, "May 2023"),
    (None, None, False, ""),
    (None, None, True, "Present"),
])
def test_date_ranges(start, end, current, expected):
    assert date_range(start, end, current) == expected


def test_month_labels():
    assert [month_label(f"2020-{m:02d}") for m in (1, 9, 12)] == ["Jan 2020", "Sep 2020", "Dec 2020"]


def test_sections_are_numbered_consecutively_and_empty_ones_skipped():
    profile = CandidateProfile(first_name="Ana", email="a@b.co", skills="Python")
    text = render_profile_markdown(profile)
    assert re.findall(r"^## (\d+)\. (.+)$", text, re.M) == [("1", "Contact Information & Links"), ("2", "Skills")]
    assert text.endswith("- Python\n")


def test_unnamed_profile_still_renders():
    assert render_profile_markdown(CandidateProfile()) == "# Candidate\n"


def test_existing_bullets_are_not_double_prefixed():
    profile = CandidateProfile(skills="- Python\n* SQL\n\nGA4")
    assert "- Python\n* SQL\n- GA4" in render_profile_markdown(profile)


def test_section_order_matches_the_example_profile():
    profile = CandidateProfile(
        first_name="A", email="a@b.co", summary="s",
        experience=[{"company": "C", "title": "T", "start_date": "2020-01", "current": True}],
        education=[{"institution": "U", "degree": "D"}],
        achievements=[{"name": "N"}], projects=[{"name": "P"}], skills="k", languages=[{"language": "L"}])
    titles = [t for _, t in re.findall(r"^## (\d+)\. (.+)$", render_profile_markdown(profile), re.M)]
    assert titles == ["Contact Information & Links", "Professional Summary", "Work Experience", "Education",
                      "Achievements", "Projects", "Skills", "Languages"]
