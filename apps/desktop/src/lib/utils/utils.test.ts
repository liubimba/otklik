import { describe, expect, it } from "vitest";
import { Utils } from "./utils";

describe("Utils.numeric.parseOptional", () => {
	// Numbers pass through unmodified — the helper trusts callers that already
	// have a number in hand and only sanitises strings from form inputs.
	it.each<[number, number]>([
		[42, 42],
		[0, 0],
		[3.7, 3.7],
		[-5, -5],
	])("numeric input parseOptional(%p) → %p", (input, expected) => {
		expect(Utils.numeric.parseOptional(input)).toBe(expected);
	});

	// String path: trim, parse, keep only positive finite integers (via
	// Math.floor), otherwise fall back to 0. Negative/zero/NaN/Infinity all
	// collapse to 0 — this is what the Settings form relies on.
	it.each<[string, number]>([
		["7", 7],
		["  7  ", 7],
		["12.5", 12],
		["1e3", 1000],
		["", 0],
		["   ", 0],
		["abc", 0],
		["-3", 0],
		["0", 0],
		["Infinity", 0],
	])("string input parseOptional(%p) → %p", (input, expected) => {
		expect(Utils.numeric.parseOptional(input)).toBe(expected);
	});
});
