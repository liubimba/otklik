import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import {
	allVacanciesPageQueryKey,
	allVacanciesQueryKey,
	invalidateAllVacancies,
} from "./all_vacancies";
import { vacanciesQueryKey } from "./vacancies";

describe("allVacanciesQueryKey", () => {
	it("does not collide with the queue's ['vacancies'] key", () => {
		expect(allVacanciesQueryKey[0]).not.toBe(vacanciesQueryKey[0]);
	});

	it("is the prefix of every page key", () => {
		const key = allVacanciesPageQueryKey(["error"], undefined, 50);
		expect(key.slice(0, 1)).toEqual([...allVacanciesQueryKey]);
	});
});

describe("allVacanciesPageQueryKey", () => {
	it("distinguishes filters, searches and limits", () => {
		expect(allVacanciesPageQueryKey(["error"], undefined, 50)).not.toEqual(
			allVacanciesPageQueryKey(["skipped"], undefined, 50),
		);
		expect(allVacanciesPageQueryKey(["error"], undefined, 50)).not.toEqual(
			allVacanciesPageQueryKey(["error"], undefined, 100),
		);
		expect(allVacanciesPageQueryKey(undefined, "go", 50)).not.toEqual(
			allVacanciesPageQueryKey(undefined, "rust", 50),
		);
	});

	it("is order-independent — ticking A then B is the same request as B then A", () => {
		expect(
			allVacanciesPageQueryKey(["skipped", "error"], undefined, 50),
		).toEqual(allVacanciesPageQueryKey(["error", "skipped"], undefined, 50));
	});

	it("normalises absent filter and search to null so the key stays stable", () => {
		expect(allVacanciesPageQueryKey(undefined, undefined, 50)).toEqual([
			"all-vacancies",
			{ statuses: null, search: null, limit: 50 },
		]);
		expect(allVacanciesPageQueryKey([], "", 50)).toEqual([
			"all-vacancies",
			{ statuses: null, search: null, limit: 50 },
		]);
	});
});

describe("invalidateAllVacancies", () => {
	it("invalidates by prefix, hitting every filter/limit variant", () => {
		const invalidateQueries = vi.fn();
		const client = { invalidateQueries } as unknown as QueryClient;

		invalidateAllVacancies(client);

		expect(invalidateQueries).toHaveBeenCalledWith({
			queryKey: allVacanciesQueryKey,
		});
	});
});
