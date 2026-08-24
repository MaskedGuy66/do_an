from pathlib import Path

import pytest

from app.services.gemini_service import (
    evaluate_cv_against_jd,
    extract_jd_criteria,
    extract_jd_criteria_from_image,
)


def test_extract_jd_criteria_from_text_returns_structured_fields():
    raw_text = (
        "Tuyển lập trình viên Python Backend. Yêu cầu: FastAPI, PostgreSQL, Docker, "
        "tối thiểu 3 năm kinh nghiệm, bằng đại học CNTT. Trách nhiệm: phát triển API, "
        "thiết kế database, triển khai hệ thống."
    )

    criteria = extract_jd_criteria(raw_text)

    assert criteria.required_skills
    assert "python" in [skill.lower() for skill in criteria.required_skills]
    assert criteria.min_years_experience >= 3
    assert criteria.education_requirement is not None
    assert criteria.key_responsibilities


def test_extract_jd_criteria_from_image_requires_valid_file():
    missing_file = Path("uploads/does_not_exist.jpg")

    with pytest.raises(FileNotFoundError):
        extract_jd_criteria_from_image(str(missing_file))


def test_extract_jd_criteria_detects_vietnamese_practical_skills():
    raw_text = (
        "Tuyển lập trình viên backend. Yêu cầu: quản trị CSDL, triển khai hệ thống, "
        "phát triển API với FastAPI, Docker, PostgreSQL. Kinh nghiệm không bắt buộc."
    )

    criteria = extract_jd_criteria(raw_text)

    normalized = {skill.lower() for skill in criteria.required_skills}
    assert any("csdl" in skill or "database" in skill for skill in normalized)
    assert any("api" in skill for skill in normalized)
    assert any("hệ thống" in skill or "system" in skill for skill in normalized)


def test_evaluate_cv_against_jd_returns_nonempty_skills_and_score_without_llm():
    jd_criteria = {
        "required_skills": ["python", "fastapi", "postgresql", "docker"],
        "preferred_skills": ["kubernetes"],
        "min_years_experience": 0,
        "education_requirement": "Đại học",
        "key_responsibilities": ["phát triển API", "quản trị CSDL"],
    }
    cv_text = (
        "Lập trình viên Python 2 năm kinh nghiệm. Tham gia dự án FastAPI, PostgreSQL, "
        "Docker; phát triển API và quản trị CSDL."
    )

    evaluation = evaluate_cv_against_jd(cv_text, jd_criteria)

    assert evaluation.total_score > 0
    assert evaluation.fit_status in {"Phù hợp", "Tiềm năng", "Loại"}
    assert evaluation.skills_match
