import { beforeEach, describe, expect, it } from "vitest";
import {
	RESERVED_APP_CHROME,
	SHEET_WIDTH_DEFAULT,
	SHEET_WIDTH_MAX,
	SHEET_WIDTH_MIN,
	SHEET_WIDTH_STORAGE_KEY,
	clampSheetWidth,
	persistSheetWidth,
	readPersistedSheetWidth,
} from "./letter-review-sheet.width";

describe("clampSheetWidth", () => {
	it("floors at SHEET_WIDTH_MIN when the user drags past the left edge", () => {
		expect(clampSheetWidth(200, 1920)).toBe(SHEET_WIDTH_MIN);
	});

	it("caps at SHEET_WIDTH_MAX when the viewport is wide enough", () => {
		expect(clampSheetWidth(2000, 1920)).toBe(SHEET_WIDTH_MAX);
	});

	it("caps below SHEET_WIDTH_MAX when the viewport is narrow (leaves RESERVED_APP_CHROME visible)", () => {
		const viewport = 800;
		expect(clampSheetWidth(2000, viewport)).toBe(
			viewport - RESERVED_APP_CHROME,
		);
	});

	it("clamps floor even when the viewport is smaller than MIN + RESERVED", () => {
		expect(clampSheetWidth(600, 500)).toBe(SHEET_WIDTH_MIN);
	});

	it("rounds fractional pixel input", () => {
		expect(clampSheetWidth(672.7, 1920)).toBe(673);
		expect(clampSheetWidth(672.4, 1920)).toBe(672);
	});

	it("falls back to SHEET_WIDTH_DEFAULT on non-finite input (corrupt localStorage)", () => {
		expect(clampSheetWidth(Number.NaN, 1920)).toBe(SHEET_WIDTH_DEFAULT);
		expect(clampSheetWidth(Number.POSITIVE_INFINITY, 1920)).toBe(
			SHEET_WIDTH_DEFAULT,
		);
	});

	it("passes through a valid mid-range value unchanged (up to rounding)", () => {
		expect(clampSheetWidth(720, 1920)).toBe(720);
	});
});

describe("readPersistedSheetWidth / persistSheetWidth", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	it("returns SHEET_WIDTH_DEFAULT (clamped) when nothing is persisted", () => {
		expect(readPersistedSheetWidth(1920)).toBe(SHEET_WIDTH_DEFAULT);
	});

	it("round-trips a valid width through localStorage", () => {
		persistSheetWidth(750);
		expect(readPersistedSheetWidth(1920)).toBe(750);
	});

	it("clamps a persisted width that no longer fits the current viewport", () => {
		persistSheetWidth(900);
		expect(readPersistedSheetWidth(800)).toBe(800 - RESERVED_APP_CHROME);
	});

	it("survives a corrupt localStorage entry — NaN parse falls back to default", () => {
		window.localStorage.setItem(SHEET_WIDTH_STORAGE_KEY, "not-a-number");
		expect(readPersistedSheetWidth(1920)).toBe(SHEET_WIDTH_DEFAULT);
	});
});
