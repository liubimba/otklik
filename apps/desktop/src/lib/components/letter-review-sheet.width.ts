/**
 * Sheet resize width helpers.
 *
 * Kept as a pure module so the clamp math can be unit tested without a
 * DOM. The component pipes pointermove deltas through `clampSheetWidth`
 * and pushes the result into an inline style on Sheet.Content.
 */

export const SHEET_WIDTH_MIN = 400;
/** Absolute cap. The viewport-aware cap in `clampSheetWidth` is always
 * min(SHEET_WIDTH_MAX, viewport - RESERVED_APP_CHROME) so the sheet
 * never eats the entire screen even on ultrawide displays. */
export const SHEET_WIDTH_MAX = 900;
/** Space reserved for the sidebar/main area on the left of the sheet.
 * Tuned to match the sidebar collapsed width + some breathing room —
 * even a maximally-wide sheet still leaves this many px visible. */
export const RESERVED_APP_CHROME = 200;
/** Default when nothing is persisted — matches the pre-refactor
 * `sm:max-w-2xl` (42rem @ 16px root). */
export const SHEET_WIDTH_DEFAULT = 672;

export const SHEET_WIDTH_STORAGE_KEY = "letter-review-sheet-width";

/**
 * Clamp a raw pixel width into a usable range.
 *
 * - Floors at SHEET_WIDTH_MIN so the textarea + footer never collapse
 *   into an unreadable strip.
 * - Caps at min(SHEET_WIDTH_MAX, viewportWidth - RESERVED_APP_CHROME)
 *   so a drag can't cover the whole app or push the resize handle
 *   off-screen where the user can't grab it back.
 * - Rounds to an integer so we don't write fractional pixels into the
 *   style attribute (Tauri/webview would just round anyway).
 * - Non-finite input (NaN from a corrupt localStorage value, ±Infinity)
 *   falls back to SHEET_WIDTH_DEFAULT.
 */
export function clampSheetWidth(raw: number, viewportWidth: number): number {
	if (!Number.isFinite(raw)) return SHEET_WIDTH_DEFAULT;
	const viewportCap = Math.max(
		SHEET_WIDTH_MIN,
		viewportWidth - RESERVED_APP_CHROME,
	);
	const cap = Math.min(SHEET_WIDTH_MAX, viewportCap);
	return Math.round(Math.max(SHEET_WIDTH_MIN, Math.min(cap, raw)));
}

/** Read the persisted width, or fall back to SHEET_WIDTH_DEFAULT. Safe
 * to call in SSR / non-browser contexts — returns the default when
 * `window` is missing. */
export function readPersistedSheetWidth(viewportWidth: number): number {
	if (typeof window === "undefined") return SHEET_WIDTH_DEFAULT;
	const raw = window.localStorage.getItem(SHEET_WIDTH_STORAGE_KEY);
	if (raw === null) return clampSheetWidth(SHEET_WIDTH_DEFAULT, viewportWidth);
	const parsed = Number.parseInt(raw, 10);
	return clampSheetWidth(parsed, viewportWidth);
}

export function persistSheetWidth(width: number): void {
	if (typeof window === "undefined") return;
	window.localStorage.setItem(SHEET_WIDTH_STORAGE_KEY, String(width));
}
