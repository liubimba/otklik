from dataclasses import dataclass


@dataclass(frozen=True)
class HabrSelectors:
    @dataclass(frozen=True)
    class SearchPage:
        title_link: str
        card: str

    @dataclass(frozen=True)
    class VacancyPage:
        title: str
        description: str
        company_name: str
        salary: str
        conditions_section: str
        section_title: str
        respond_button: str
        responded_marker: str

    @dataclass(frozen=True)
    class Captcha:
        marker: str | None = None

    search: SearchPage
    vacancy: VacancyPage
    captcha: Captcha


HABR_SELECTORS = HabrSelectors(
    search=HabrSelectors.SearchPage(
        title_link="a.vacancy-card__title-link",
        card="div.vacancy-card",
    ),
    vacancy=HabrSelectors.VacancyPage(
        title="h1.page-title__title",
        description=".vacancy-description__text",
        company_name=".company_name",
        salary=".basic-salary",
        conditions_section=".content-section",
        section_title=".content-section__title",
        respond_button="button.button-comp--appearance-main",
        responded_marker=".vacancy-responses, .vacancy-response--responded",
    ),
    captcha=HabrSelectors.Captcha(marker=None),
)
