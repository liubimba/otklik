from headhunter_backend.db.models import (
    VacancyORM,
    SettingsORM,
    SearchHistoryORM,
    ApplicationORM,
    CoverLetterORM,
)
from headhunter_backend.api.schemas import (
    EmploymentType,
    WorkFormat,
    VacancyAPISchema,
    SearchHistoryAPISchema,
    LLMSettingsAPISchema,
    SearchSettingsAPISchema,
    SettingsAPISchema,
    RateLimitsAPISchema,
    UserSettingsAPISchema,
    ApplicationAPISchema,
    CoverLetterAPISchema,
)


def settings_to_orm(schema: SettingsAPISchema) -> SettingsORM:
    return SettingsORM(
        letter_style=schema.llm.letter_style,
        resume_text=schema.llm.resume_text,
        daily_limit=schema.rate_limits.daily_limit,
        hourly_limit=schema.rate_limits.hourly_limit,
        min_delay_ms=schema.rate_limits.min_delay_ms,
        delay_jitter_ms=schema.rate_limits.delay_jitter_ms,
        llm_deployments=schema.llm.deployments,
        llm_system_prompt=schema.llm.system_prompt,
        auto_submit=schema.user.auto_submit,
        max_vacancies=schema.search.max_vacancies,
        max_pages=schema.search.max_pages,
    )


def settings_to_schema(orm: SettingsORM) -> SettingsAPISchema:
    return SettingsAPISchema(
        rate_limits=RateLimitsAPISchema(
            daily_limit=orm.daily_limit,
            hourly_limit=orm.hourly_limit,
            min_delay_ms=orm.min_delay_ms,
            delay_jitter_ms=orm.delay_jitter_ms,
        ),
        llm=LLMSettingsAPISchema(
            deployments=orm.llm_deployments,
            system_prompt=orm.llm_system_prompt,
            letter_style=orm.letter_style,
            resume_text=orm.resume_text,
        ),
        user=UserSettingsAPISchema(auto_submit=orm.auto_submit),
        search=SearchSettingsAPISchema(
            max_pages=orm.max_pages,
            max_vacancies=orm.max_vacancies,
        ),
    )


def vacancy_to_orm(schema: VacancyAPISchema) -> VacancyORM:
    return VacancyORM(
        title=schema.title,
        apply_link=schema.apply_link,
        description=schema.description,
        company_stars=schema.company_stars,
        salary=schema.salary,
        company_name=schema.company_name,
        work_location=schema.work_location,
        updated_at=schema.updated_at,
        published_at=schema.published_at,
        work_experience=schema.work_experience,
        work_formats=[wf.value for wf in schema.work_formats],
        employment_types=[et.value for et in schema.employment_types],
        response_link=schema.response_link,
    )


def vacancy_to_schema(row: VacancyORM) -> VacancyAPISchema:
    return VacancyAPISchema(
        id=row.id,
        title=row.title,
        apply_link=row.apply_link,
        description=row.description,
        company_stars=row.company_stars,
        salary=row.salary,
        company_name=row.company_name,
        work_location=row.work_location,
        updated_at=row.updated_at,
        published_at=row.published_at,
        work_experience=row.work_experience,
        work_formats=[WorkFormat(v) for v in row.work_formats],
        employment_types=[EmploymentType(v) for v in row.employment_types],
        response_link=row.response_link,
    )


def search_history_to_schema(orm: SearchHistoryORM) -> SearchHistoryAPISchema:
    return SearchHistoryAPISchema(
        id=orm.id,
        url=orm.url,
        max_vacancies=orm.max_vacancies,
        max_pages=orm.max_pages,
        status=orm.status,
        parsed_vacancies=orm.parsed_vacancies,
        parsed_pages=orm.parsed_pages,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        error=orm.error,
    )


def application_to_schema(orm: ApplicationORM) -> ApplicationAPISchema:
    return ApplicationAPISchema(
        vacancy_id=orm.vacancy_id,
        retry_count=orm.retry_count,
        application_id=orm.id,
        created_at=orm.created_at,
        status=orm.status,
        updated_at=orm.updated_at,
        error_message=orm.error_message,
    )


def cover_letter_to_schema(orm: CoverLetterORM) -> CoverLetterAPISchema:
    return CoverLetterAPISchema(
        version=orm.version, text=orm.text, created_at=orm.created_at
    )
