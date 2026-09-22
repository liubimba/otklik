from dataclasses import dataclass


@dataclass(frozen=True)
class KworkResponseSelectors:
    offer_button: str
    form_marker: str
    message_editor: str
    price_input: str
    order_name_editor: str
    payment_type_option: str
    buyer_budget: str
    delivery_toggle: str
    delivery_input: str
    delivery_option: str
    submit_button: str
    error_message: str
    already_responded_marker: str


KWORK_RESPONSE = KworkResponseSelectors(
    offer_button='.projects-offer-btn:has-text("Предложить услугу")',
    form_marker=".modal-individual-offer, .custom-kwork-offer__wrapper",
    message_editor=".modal-individual-offer__desc .trumbowyg-editor",
    price_input="#offer-custom-price",
    order_name_editor=".modal-individual-offer__name .trumbowyg-editor",
    payment_type_option=".offer-payment-type__item",
    buyer_budget=".offer-individual__higher-price",
    delivery_toggle=".duration-select .vs__dropdown-toggle",
    delivery_input=".duration-select input.vs__search",
    delivery_option='ul[id^="vs"] li',
    submit_button=".modal-individual-offer__footer button.kw-button--green",
    error_message=".offer-individual__error",
    already_responded_marker=".want-card__offer-sent, .offer-sent, .js-offer-sent",
)
