import type { SearchEvent, Vacancy, VacancyEvent } from "$lib/api/types";
import type { QueryClient } from "@tanstack/svelte-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	applySearchEvent,
	applyVacancyEvent,
	vacanciesQueryKey,
} from "./vacancies";

function makeFakeQueryClient() {
	let seeded: Vacancy[] | undefined;
	const setQueryData = vi.fn(
		(_key: unknown, updater: (prev: Vacancy[] | undefined) => Vacancy[]) => {
			seeded = updater(seeded);
		},
	);
	const invalidateQueries = vi.fn();
	return {
		client: { setQueryData, invalidateQueries } as unknown as QueryClient,
		setQueryData,
		invalidateQueries,
		seed(data: Vacancy[] | undefined) {
			seeded = data;
		},
		read: () => seeded,
	};
}

const vacancy = (id: number, title = `Vacancy ${id}`): Vacancy => ({
	id,
	title,
	apply_link: `https://hh.ru/vacancy/${id}`,
	description: "d",
	company_stars: null,
	salary: null,
	company_name: null,
	work_location: null,
	updated_at: null,
	published_at: null,
	work_formats: [],
	employment_types: [],
	work_experience: null,
});

const vacancyEvent = (v: Vacancy): VacancyEvent => ({
	type: "vacancy_new",
	data: v,
	search_id: null,
});

const searchEvent = (status: SearchEvent["data"]["status"]): SearchEvent => ({
	type: "search_event",
	data: {
		search_id: "s",
		parsed_pages: 1,
		parsed_vacancies: 2,
		status,
	},
});

describe("applyVacancyEvent", () => {
	let fake: ReturnType<typeof makeFakeQueryClient>;
	beforeEach(() => {
		fake = makeFakeQueryClient();
	});

	it("prepends a new vacancy to the cached list", () => {
		fake.seed([vacancy(2)]);
		applyVacancyEvent(fake.client, vacancyEvent(vacancy(3)));

		expect(fake.read()?.map((v) => v.id)).toEqual([3, 2]);
	});

	it("dedupes by id (updated vacancy replaces the older entry)", () => {
		fake.seed([vacancy(1, "old"), vacancy(2)]);
		applyVacancyEvent(fake.client, vacancyEvent(vacancy(1, "fresh")));

		const list = fake.read();
		expect(list?.map((v) => v.id)).toEqual([1, 2]);
		expect(list?.[0].title).toBe("fresh");
	});

	it("seeds the list when the cache is empty", () => {
		applyVacancyEvent(fake.client, vacancyEvent(vacancy(9)));
		expect(fake.read()?.map((v) => v.id)).toEqual([9]);
	});

	it("writes under the shared vacanciesQueryKey", () => {
		applyVacancyEvent(fake.client, vacancyEvent(vacancy(1)));
		expect(fake.setQueryData).toHaveBeenCalledWith(
			vacanciesQueryKey,
			expect.any(Function),
		);
	});
});

describe("applySearchEvent — invalidation gating", () => {
	let fake: ReturnType<typeof makeFakeQueryClient>;
	beforeEach(() => {
		fake = makeFakeQueryClient();
	});

	it.each(["exited", "canceled", "failed", "interrupted"] as const)(
		"invalidates on terminal status=%s",
		(status) => {
			applySearchEvent(fake.client, searchEvent(status));
			expect(fake.invalidateQueries).toHaveBeenCalledWith({
				queryKey: vacanciesQueryKey,
			});
		},
	);

	it.each(["pending", "running"] as const)(
		"does NOT invalidate on active status=%s",
		(status) => {
			applySearchEvent(fake.client, searchEvent(status));
			expect(fake.invalidateQueries).not.toHaveBeenCalled();
		},
	);
});
