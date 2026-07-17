import { describe, expect, it } from "vitest";
import { Utils } from "./utils";

describe("Utils.numeric.parseOptional", () => {
	it.each<[number, number]>([
		[42, 42],
		[0, 0],
		[3.7, 3.7],
		[-5, -5],
	])("numeric input parseOptional(%p) → %p", (input, expected) => {
		expect(Utils.numeric.parseOptional(input)).toBe(expected);
	});

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
