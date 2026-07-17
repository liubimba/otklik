export const SHEET_WIDTH_MIN = 400;
export const SHEET_WIDTH_MAX = 900;
export const RESERVED_APP_CHROME = 200;
export const SHEET_WIDTH_DEFAULT = 672;

export const SHEET_WIDTH_STORAGE_KEY = "letter-review-sheet-width";

export function clampSheetWidth(raw: number, viewportWidth: number): number {
	if (!Number.isFinite(raw)) return SHEET_WIDTH_DEFAULT;
	const viewportCap = Math.max(
		SHEET_WIDTH_MIN,
		viewportWidth - RESERVED_APP_CHROME,
	);
	const cap = Math.min(SHEET_WIDTH_MAX, viewportCap);
	return Math.round(Math.max(SHEET_WIDTH_MIN, Math.min(cap, raw)));
}

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
