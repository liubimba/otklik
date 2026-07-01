# HH-specific submission writer. See parser.py header — same migration
# pattern. Physical body currently lives in browser/writer.py.
from headhunter_backend.browser.writer import BrowserWriter as HHRUWriter

__all__ = ["HHRUWriter"]
