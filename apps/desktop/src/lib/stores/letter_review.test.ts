import { describe, expect, it } from "vitest";
import { LetterReviewStore } from "./letter_review.svelte";

describe("LetterReviewStore", () => {
	it("starts closed (vacancyId=null)", () => {
		const store = new LetterReviewStore();
		expect(store.vacancyId).toBeNull();
	});

	it("open() sets the vacancyId", () => {
		const store = new LetterReviewStore();
		store.open(42);
		expect(store.vacancyId).toBe(42);
	});

	it("close() clears the vacancyId back to null", () => {
		const store = new LetterReviewStore();
		store.open(7);
		store.close();
		expect(store.vacancyId).toBeNull();
	});

	it("open() replaces the previously open vacancy without an explicit close", () => {
		const store = new LetterReviewStore();
		store.open(1);
		store.open(2);
		expect(store.vacancyId).toBe(2);
	});

	it("close() is idempotent on an already closed store", () => {
		const store = new LetterReviewStore();
		store.close();
		expect(store.vacancyId).toBeNull();
		store.close();
		expect(store.vacancyId).toBeNull();
	});
});
