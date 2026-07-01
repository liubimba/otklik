# SiteSelectors is currently a structural alias for browser.Selectors — every
# site provides a Selectors-shaped dataclass with the same field family. As
# more sites land the concrete Selectors class here should become a Protocol
# or a per-field family of dataclasses.
from headhunter_backend.browser.selectors import Selectors as SiteSelectors

__all__ = ["SiteSelectors"]
