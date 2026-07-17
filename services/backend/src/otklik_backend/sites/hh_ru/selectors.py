from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Selectors:
    @dataclass(frozen=True)
    class SearchPage:
        apply_link: str
        vacancy_card: str
        response_link_serp_card: str

    @dataclass(frozen=True)
    class VacancyPage:
        title: str
        description: str

        company_stars: str
        salary: str
        company_name: str
        work_location: str
        updated_at: Optional[str]
        published_at: Optional[str]
        work_format: str
        work_experience: str
        employment_type: str
        respond_link_top: str

    @dataclass(frozen=True)
    class VacancyResponsePage:
        respond_button: str
        open_letter_textarea_button: str
        letter_textarea: str
        success_marker: str | None = None

    @dataclass(frozen=True)
    class Captcha:
        marker: str | None = None

    search: SearchPage
    vacancy: VacancyPage
    response: VacancyResponsePage
    captcha: Captcha


HHRU_SELECTORS = Selectors(
    search=Selectors.SearchPage(
        apply_link='[data-qa="serp-item__title"]',
        vacancy_card='[data-qa~="vacancy-serp__vacancy"]',
        response_link_serp_card='[data-qa="vacancy-serp__vacancy_response"]',
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
        respond_link_top='[data-qa="vacancy-response-link-top"]',
    ),
    response=Selectors.VacancyResponsePage(
        respond_button='[data-qa="vacancy-response-submit-popup"]',
        letter_textarea='[data-qa="vacancy-response-popup-form-letter-input"]',
        open_letter_textarea_button='[data-qa="add-cover-letter"]',
    ),
    captcha=Selectors.Captcha(),
)
