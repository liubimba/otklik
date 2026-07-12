from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Selectors:
    @dataclass(frozen=True)
    class SearchPage:
        apply_link: str
        vacancy_card: str
        # Respond-link element inside a SERP card. Used ONLY by
        # parser._normalize_ad_href — the href carries a `vacancyId` query
        # param that lets us reconstruct the canonical /vacancy/{id} URL
        # when the card's title-link is an adsrv.hh.ru redirect. Not a
        # user-facing field, not stored per vacancy — that column was
        # dropped in migration c1e5b8f92a04 (2026-07-02) after the "text
        # instead of URL" bug was fixed by switching the writer to
        # apply_link.
        response_link_serp_card: str

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
        # Top respond link on the detail page — an <a href="/applicant/
        # vacancy_response?...">Откликнуться</a> that hh.ru rendered as
        # a magritte-button. Writer clicks this to leave the detail page
        # and land on the response form. Kept as a Vacancy-page selector
        # because it lives on the detail DOM, not on the response form.
        respond_link_top: str

    @dataclass(frozen=True)
    class VacancyResponsePage:
        # Selectors inside the response modal that hh.ru pops open after
        # a click on vacancy.respond_link_top. The dialog carries
        # role="dialog", a hidden _xsrf, a resume-picker card, and two
        # footer buttons: "Добавить сопроводительное" (opens the letter
        # textarea) and the primary "Откликнуться" (final submit).
        # `letter_textarea` still targets the pre-magritte data-qa —
        # verify against a fresh HTML sample after clicking
        # "Добавить сопроводительное" if the writer starts failing at
        # step 5 (see test_hhru_writer for the pinned order).
        respond_button: str
        open_letter_textarea_button: str
        letter_textarea: str
        success_marker: str | None = None  # TODO Need to determine selector

    @dataclass(frozen=True)
    class Captcha:
        marker: str | None = None  # TODO Need to determine selector

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
        # Renamed by hh.ru mid-2026 from `vacancy-response-letter-toggle`
        # to `add-cover-letter` when the whole response UI was ported to
        # the magritte design system.
        open_letter_textarea_button='[data-qa="add-cover-letter"]',
    ),
    captcha=Selectors.Captcha(),
)
