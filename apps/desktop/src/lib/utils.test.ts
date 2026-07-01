import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn — Tailwind class merger", () => {
	it("joins plain classes", () => {
		expect(cn("a", "b", "c")).toBe("a b c");
	});

	it("dedupes Tailwind conflicts (last wins)", () => {
		expect(cn("p-2", "p-4")).toBe("p-4");
		expect(cn("text-sm text-lg")).toBe("text-lg");
	});

	it("handles conditional classes via clsx", () => {
		expect(cn("a", false && "b", "c", { d: true, e: false })).toBe("a c d");
	});

	it("supports arrays and nested inputs", () => {
		expect(cn(["a", ["b", { c: true }]])).toBe("a b c");
	});

	it("returns empty string for no truthy inputs", () => {
		expect(cn(false, null, undefined, "")).toBe("");
	});
});
