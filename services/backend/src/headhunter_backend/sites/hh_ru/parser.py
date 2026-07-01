# HH-specific vacancy list-page + detail-page parser. The implementation is
# still physically in browser/parser.py during the multi-site migration;
# this module makes the domain-role name (`HHRUParser`) load-bearing so new
# call sites depend on the site package instead of `browser/`. When a second
# site lands, the physical body moves here.
from headhunter_backend.browser.parser import Parser as HHRUParser

__all__ = ["HHRUParser"]
