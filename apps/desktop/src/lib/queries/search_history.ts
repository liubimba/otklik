import { API } from "$lib/api/client";
import type { SearchEvent, SearchHistory } from "$lib/api/types";
import type { BoardKind } from "$lib/boards";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const searchHistoryQueryKey = ["search", "history"] as const;

export function searchHistoryBoardQueryKey(board?: BoardKind) {
	return [...searchHistoryQueryKey, board ?? null];
}

export function createSearchHistoryQuery(
	getBoard?: () => BoardKind | undefined,
) {
	return createQuery<SearchHistory[]>(() => {
		const board = getBoard?.();
		return {
			queryKey: searchHistoryBoardQueryKey(board),
			queryFn: () => API.search.history.list(board),
			staleTime: 30_000,
		};
	});
}

export function applySearchHistoryEvent(
	queryClient: QueryClient,
	_event: SearchEvent,
): void {
	queryClient.invalidateQueries({ queryKey: searchHistoryQueryKey });
}
