import { API } from "$lib/api/client";
import type { VacancyListPage, VacancyStatusFilter } from "$lib/api/types";
import {
	type QueryClient,
	createQuery,
	keepPreviousData,
} from "@tanstack/svelte-query";

// Deliberately NOT ["vacancies"] — that key holds the current search's list and
// is mutated in place by applyVacancyEvent (prepend + dedupe). The archive is a
// paginated, filtered envelope and must not collide with it.
export const allVacanciesQueryKey = ["all-vacancies"] as const;

export function allVacanciesPageQueryKey(
	statuses: readonly VacancyStatusFilter[] | undefined,
	search: string | undefined,
	limit: number,
) {
	// Chip order is a UI accident, not part of the request — sort so that
	// ticking A then B hits the same cache entry as ticking B then A.
	const sorted = statuses?.length ? [...statuses].sort() : null;
	return [
		...allVacanciesQueryKey,
		{ statuses: sorted, search: search || null, limit },
	];
}

/**
 * One page of the archive. Pagination is "load more" by growing `limit` rather
 * than an infinite query: the cache stays a single {items,total} envelope, which
 * a plain prefix invalidation can refresh. `keepPreviousData` keeps the current
 * rows on screen while the wider page loads.
 */
export function createAllVacanciesQuery(
	getStatuses: () => readonly VacancyStatusFilter[] | undefined,
	getSearch: () => string | undefined,
	getLimit: () => number,
	// TanStack's escape hatch for callers outside a QueryClientProvider — the
	// page never passes it; the reactivity test does. It wants a getter.
	getQueryClient?: () => QueryClient,
) {
	return createQuery<VacancyListPage>(() => {
		// An all-whitespace box is no filter at all — normalise it away so it
		// neither reaches the wire nor forks the cache.
		const search = getSearch()?.trim() || undefined;
		const statuses = getStatuses()?.length ? getStatuses() : undefined;
		return {
			queryKey: allVacanciesPageQueryKey(statuses, search, getLimit()),
			queryFn: () =>
				API.vacancies.listAll({ statuses, search, limit: getLimit() }),
			placeholderData: keepPreviousData,
			staleTime: 30_000,
		};
	}, getQueryClient);
}

/**
 * Cards on the archive page read their status from the list payload, so nothing
 * refreshes it except a refetch of the list itself. Both `vacancy_new` and
 * `application_event` can change what this page should show, and neither can be
 * patched in honestly: the event carries no status, and an active filter may
 * exclude the row entirely. Invalidate and let the mounted query refetch —
 * unmounted ones cost nothing.
 */
export function invalidateAllVacancies(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: allVacanciesQueryKey });
}
