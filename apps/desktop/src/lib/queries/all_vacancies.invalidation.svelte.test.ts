import { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";

const listAll = vi.hoisted(() => vi.fn());

vi.mock("$lib/api/client", () => ({
	API: { vacancies: { listAll } },
}));

import type { VacancyStatusFilter } from "$lib/api/types";
import {
	createAllVacanciesQuery,
	invalidateAllVacancies,
} from "./all_vacancies";

function flush() {
	return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("createAllVacanciesQuery — filtering while a search streams events", () => {
	it("applies a newly toggled status filter despite a flood of invalidations", async () => {
		listAll.mockResolvedValue({ items: [], total: 0 });
		const queryClient = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});

		let statuses = $state<VacancyStatusFilter[]>([]);
		const cleanup = $effect.root(() => {
			createAllVacanciesQuery(
				() => statuses,
				() => "",
				() => 50,
				() => "latest",
				() => queryClient,
			);
		});

		await flush();
		expect(listAll).toHaveBeenCalledTimes(1);

		for (let i = 0; i < 5; i++) {
			invalidateAllVacancies(queryClient);
			await flush();
		}

		listAll.mockClear();
		statuses = ["letter_sent"];
		await flush();
		invalidateAllVacancies(queryClient);
		await flush();

		const sawFilter = listAll.mock.calls.some(
			(call) =>
				JSON.stringify(call[0]?.statuses) === JSON.stringify(["letter_sent"]),
		);
		expect(sawFilter).toBe(true);
		const lastCall = listAll.mock.calls.at(-1);
		expect(lastCall?.[0]).toMatchObject({ statuses: ["letter_sent"] });
	});
});
