from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "task-delivery-rca" / "SKILL.md"
BANNED_SCENARIO_TEXT = {
    "aarav",
    "maya",
    "kabir",
    "emp001",
    "emp002",
    "emp003",
    "ownership mismatch",
    "access exception required",
    "recommended product analytics owner",
}


def test_skill_file_exists_and_contains_rca_funnel():
    text = SKILL_PATH.read_text()

    assert "Top-Funnel Eligibility" in text
    assert "Evidence Filter" in text
    assert "Primary Cause" in text
    assert "Contributing Factors" in text
    assert "Rejected Causes" in text


def test_skill_has_no_case_specific_answer_leakage():
    text = SKILL_PATH.read_text().lower()

    for phrase in BANNED_SCENARIO_TEXT:
        assert phrase not in text, phrase


def test_skill_requires_dynamic_specialists_and_mandatory_reviewer():
    text = SKILL_PATH.read_text().lower()

    assert "use evidence specialists dynamically" in text
    assert "always use the evidence privacy reviewer" in text
    assert "not relevant" in text


def test_skill_distinguishes_fact_observation_inference_and_conclusion():
    text = SKILL_PATH.read_text().lower()

    assert "a fact is" in text
    assert "an observation" in text
    assert "an inference" in text
    assert "a conclusion" in text


def test_skill_allows_insufficient_evidence():
    text = SKILL_PATH.read_text().lower()

    assert "insufficient_evidence" in text
    assert "do not invent a candidate" in text
