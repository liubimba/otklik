import { API } from "$lib/api/client";
import type { SearchEvent, SearchHistory } from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const searchHistoryQueryKey = ["search", "history"] as const;

export function createSearchHistoryQuery() {
	return createQuery<SearchHistory[]>(() => ({
		queryKey: searchHistoryQueryKey,
		queryFn: () => API.search.history.list(),
		staleTime: 30_000,
	}));
}

// A running search continuously mutates its `searches` row (status, counts,
// finished_at), so any `search_event` may have changed the history list —
// refetch it. Cheap: the list only re-fetches while the /history page keeps
// the query mounted.
export function applySearchHistoryEvent(
	queryClient: QueryClient,
	_event: SearchEvent,
): void {
	queryClient.invalidateQueries({ queryKey: searchHistoryQueryKey });
}
