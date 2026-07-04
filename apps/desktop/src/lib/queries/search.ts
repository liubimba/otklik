import { API } from "$lib/api/client";
import {
	type SearchData,
	type SearchEvent,
	TERMINAL_SEARCH_STATUSES,
} from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const currentSearchQueryKey = ["search", "current"];

export function createCurrentSearchQuery() {
	return createQuery<SearchData | null>(() => ({
		queryKey: currentSearchQueryKey,
		queryFn: API.search.parse.current,
		staleTime: Number.POSITIVE_INFINITY,
	}));
}

export function applyCurrentSearchEvent(
	queryClient: QueryClient,
	event: SearchEvent,
): void {
	const next = TERMINAL_SEARCH_STATUSES.has(event.data.status)
		? null
		: event.data;
	queryClient.setQueryData(currentSearchQueryKey, next);
}
