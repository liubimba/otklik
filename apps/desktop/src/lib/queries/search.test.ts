import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import type { SearchEvent } from "$lib/api/types";
import { applyCurrentSearchEvent, currentSearchQueryKey } from "./search";

function makeFakeQueryClient() {
	const setQueryData = vi.fn();
	return {
		client: { setQueryData } as unknown as QueryClient,
		setQueryData,
	};
}

const searchEvent = (status: SearchEvent["data"]["status"]): SearchEvent => ({
	type: "search_event",
	data: {
		search_id: "sid",
		parsed_pages: 3,
		parsed_vacancies: 10,
		status,
	},
});

describe("applyCurrentSearchEvent", () => {
	it.each(["pending", "running"] as const)(
		"writes the event data when active (status=%s)",
		(status) => {
			const { client, setQueryData } = makeFakeQueryClient();
			const event = searchEvent(status);

			applyCurrentSearchEvent(client, event);

			expect(setQueryData).toHaveBeenCalledWith(
				currentSearchQueryKey,
				event.data,
			);
		},
	);

	it.each(["exited", "canceled", "failed", "interrupted"] as const)(
		"clears the cache (sets null) on terminal status=%s",
		(status) => {
			const { client, setQueryData } = makeFakeQueryClient();

			applyCurrentSearchEvent(client, searchEvent(status));

			expect(setQueryData).toHaveBeenCalledWith(currentSearchQueryKey, null);
		},
	);

	it("uses a stable query key across calls", () => {
		const { client, setQueryData } = makeFakeQueryClient();

		applyCurrentSearchEvent(client, searchEvent("running"));
		applyCurrentSearchEvent(client, searchEvent("exited"));

		const firstKey = setQueryData.mock.calls[0][0];
		const secondKey = setQueryData.mock.calls[1][0];
		expect(firstKey).toBe(secondKey);
	});
});
