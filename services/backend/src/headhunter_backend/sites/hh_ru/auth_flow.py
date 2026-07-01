# HH-specific auth flow. BrowserCore currently implements the SiteAuthFlow
# protocol structurally (get_auth_status / wait_for_login / unauthorize).
# The clean split — generic Playwright lifecycle in browser/core.py,
# HH-specific login page detection in an HHRUAuthFlow class — lands with
# the second site's arrival; for now the browser core is the HH auth flow.
from headhunter_backend.browser.core import BrowserCore as HHRUAuthFlow

__all__ = ["HHRUAuthFlow"]
