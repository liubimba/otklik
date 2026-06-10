from headhunter_backend.ai.prompts import PromptBuilder
from headhunter_backend.api.schemas import EmploymentType, VacancyAPISchema, WorkFormat


def _make_vacancy(**overrides) -> VacancyAPISchema:
    defaults: dict = dict(
        title="Python Developer",
        apply_link="https://hh.ru/vacancy/12345",
        description="Build and ship backend services.",
        company_name="ACME",
        salary="200000 RUB",
        work_location="Moscow",
        work_formats=[WorkFormat.REMOTE],
        employment_types=[EmploymentType.FULL_TIME],
        work_experience="1-3 years",
    )
    defaults.update(overrides)
    return VacancyAPISchema(**defaults)


def _system(messages) -> str:
    assert messages[0]["role"] == "system"
    return messages[0]["content"]


def _user(messages) -> str:
    assert messages[1]["role"] == "user"
    return messages[1]["content"][0]["text"]


def test_empty_style_does_not_append_tone_section() -> None:
    messages = PromptBuilder().build_cover_letter_prompt(
        vacancy_model=_make_vacancy(), resume="resume", style=""
    )
    assert "Tone and style of the letter:" not in _system(messages)


def test_whitespace_only_style_does_not_append_tone_section() -> None:
    messages = PromptBuilder().build_cover_letter_prompt(
        vacancy_model=_make_vacancy(), resume="resume", style="   \n\t"
    )
    assert "Tone and style of the letter:" not in _system(messages)


def test_style_is_appended_and_trimmed() -> None:
    messages = PromptBuilder().build_cover_letter_prompt(
        vacancy_model=_make_vacancy(), resume="resume", style="  laid-back  "
    )
    assert "Tone and style of the letter: laid-back." in _system(messages)


def test_custom_system_prompt_overrides_default() -> None:
    messages = PromptBuilder().build_cover_letter_prompt(
        vacancy_model=_make_vacancy(),
        resume="resume",
        style="",
        system_prompt="Custom system instructions.",
    )
    system: str = _system(messages)
    assert system == "Custom system instructions."
    assert "personalized cover letters" not in system


def test_custom_system_prompt_still_accepts_style() -> None:
    messages = PromptBuilder().build_cover_letter_prompt(
        vacancy_model=_make_vacancy(),
        resume="resume",
        style="formal",
        system_prompt="Custom system instructions.",
    )
    system: str = _system(messages)
    assert system.startswith("Custom system instructions.")
    assert "Tone and style of the letter: formal." in system


def test_user_message_contains_vacancy_position_and_company() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(title="Senior Backend", company_name="ACME"),
            resume="resume",
            style="",
        )
    )
    assert "- Position: Senior Backend" in user
    assert "- Company: ACME" in user


def test_user_message_skips_none_fields() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(
                company_name=None, salary=None, work_location=None, work_experience=None
            ),
            resume="resume",
            style="",
        )
    )
    assert "- Position:" in user
    assert "- Company:" not in user
    assert "- Salary:" not in user
    assert "- Location:" not in user
    assert "- Required experience:" not in user


def test_user_message_filters_unknown_work_format() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(
                work_formats=[WorkFormat.REMOTE, WorkFormat.UNKNOWN]
            ),
            resume="resume",
            style="",
        )
    )
    assert "- Work format: remote" in user
    assert "unknown" not in user


def test_user_message_omits_work_format_line_when_all_unknown() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(work_formats=[WorkFormat.UNKNOWN]),
            resume="resume",
            style="",
        )
    )
    assert "- Work format:" not in user


def test_user_message_filters_unknown_employment_type() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(
                employment_types=[EmploymentType.FULL_TIME, EmploymentType.UNKNOWN]
            ),
            resume="resume",
            style="",
        )
    )
    assert "- Employment type: full_time" in user
    assert "Employment type: full_time, unknown" not in user


def test_user_message_joins_multiple_known_work_formats() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(
                work_formats=[WorkFormat.REMOTE, WorkFormat.HYBRID]
            ),
            resume="resume",
            style="",
        )
    )
    assert "- Work format: remote, hybrid" in user


def test_user_message_includes_description_and_resume() -> None:
    user: str = _user(
        PromptBuilder().build_cover_letter_prompt(
            vacancy_model=_make_vacancy(description="Job duties go here."),
            resume="My resume body.",
            style="",
        )
    )
    assert "# Job description\nJob duties go here." in user
    assert "# Resume\nMy resume body." in user
    assert user.rstrip().endswith("Write the cover letter now.")


def test_default_system_prompt_includes_anti_placeholder_rule() -> None:
    messages = PromptBuilder().build_cover_letter_prompt(
        vacancy_model=_make_vacancy(), resume="resume", style=""
    )
    system: str = _system(messages)
    assert "bracketed placeholders" in system
    assert "[Company]" in system or "[Position]" in system


def test_build_ping_returns_single_user_message() -> None:
    messages = PromptBuilder().build_ping()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"] == "ping"
