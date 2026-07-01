import { describe, expect, it } from "vitest";
import { TERMINAL_SEARCH_STATUSES } from "./types";
import type { SearchStatus } from "./types";

describe("TERMINAL_SEARCH_STATUSES", () => {
	it.each<[SearchStatus, boolean]>([
		["exited", true],
		["canceled", true],
		["failed", true],
		["interrupted", true],
		["pending", false],
		["running", false],
	])("has(%p) === %p", (status, expected) => {
		expect(TERMINAL_SEARCH_STATUSES.has(status)).toBe(expected);
	});

	it("is exactly the four terminal states", () => {
		expect(Array.from(TERMINAL_SEARCH_STATUSES).sort()).toEqual(
			["canceled", "exited", "failed", "interrupted"].sort(),
		);
	});
});
