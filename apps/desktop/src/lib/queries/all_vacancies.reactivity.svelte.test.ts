import { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";

const listAll = vi.hoisted(() => vi.fn());

vi.mock("$lib/api/client", () => ({
	API: { vacancies: { listAll } },
}));

import { createAllVacanciesQuery } from "./all_vacancies";

function flush() {
	return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("createAllVacanciesQuery — reactivity", () => {
	it("refetches with the new search text when the getter's state changes", async () => {
		listAll.mockResolvedValue({ items: [], total: 0 });
		const queryClient = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});

		let search = $state("");
		const cleanup = $effect.root(() => {
			createAllVacanciesQuery(
				() => undefined,
				() => search,
				() => 50,
				() => queryClient,
			);
		});

		await flush();
		expect(listAll).toHaveBeenCalledTimes(1);
		expect(listAll.mock.calls[0][0]).toMatchObject({ search: undefined });

		search = "python";
		await flush();

		expect(listAll).toHaveBeenCalledTimes(2);
		expect(listAll.mock.calls[1][0]).toMatchObject({ search: "python" });

		cleanup();
	});
});
