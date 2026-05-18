from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Selectors:
    @dataclass(frozen=True)
    class SearchPage:
        apply_link: str
        vacancy_card: str
        response_link: str

    @dataclass(frozen=True)
    class VacancyPage:
        title: str
        description: str

        company_stars: str
        salary: str
        company_name: str
        work_location: str
        updated_at: Optional[str]  # TODO Need to determine selector
        published_at: Optional[str]  # TODO Need to determine selector
        work_format: str
        work_experience: str
        employment_type: str

    search: SearchPage
    vacancy: VacancyPage


HHRU_SELECTORS = Selectors(
    search=Selectors.SearchPage(
        apply_link='[data-qa="serp-item__title"]',
        vacancy_card='[data-qa~="vacancy-serp__vacancy"]',
        response_link='[data-qa="vacancy-serp__vacancy_response"]',
    ),
    vacancy=Selectors.VacancyPage(
        title='[data-qa="vacancy-title"]',
        description='[data-qa="vacancy-description"]',
        company_stars='[data-qa="employer-review-small-widget-total-rating"]',
        salary='[data-qa="vacancy-salary"]',
        company_name='[data-qa="vacancy-company-name"]',
        work_location='[data-qa="vacancy-view-raw-address"]',
        updated_at=None,
        published_at=None,
        work_format='[data-qa="work-formats-text"]',
        work_experience='[data-qa="work-experience-text"]',
        employment_type='[data-qa="common-employment-text"]',
    ),
)
