from dataclasses import dataclass


@dataclass(frozen=True)
class KworkResponseSelectors:
    offer_button: str
    form_marker: str
    message_editor: str
    price_input: str
    order_name_editor: str
    buyer_budget: str
    delivery_input: str
    delivery_option: str
    submit_button: str
    already_responded_marker: str


KWORK_RESPONSE = KworkResponseSelectors(
    offer_button='.projects-offer-btn:has-text("Предложить услугу")',
    form_marker=".modal-individual-offer, .custom-kwork-offer__wrapper",
    message_editor=".modal-individual-offer__desc .trumbowyg-editor",
    price_input="#offer-custom-price",
    order_name_editor=".modal-individual-offer__name .trumbowyg-editor",
    buyer_budget=".offer-individual__higher-price",
    delivery_input=".duration-select input.vs__search",
    delivery_option=".duration-select__dropdown li",
    submit_button=".modal-individual-offer__footer button.kw-button--green",
    already_responded_marker=".want-card__offer-sent, .offer-sent, .js-offer-sent",
)
