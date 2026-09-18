import { API } from "$lib/api/client";
import type { VacancyListPage, VacancyStatusFilter } from "$lib/api/types";
import type { BoardKind } from "$lib/boards";
import {
	type QueryClient,
	createQuery,
	keepPreviousData,
} from "@tanstack/svelte-query";

export const allVacanciesQueryKey = ["all-vacancies"] as const;

export function allVacanciesPageQueryKey(
	statuses: readonly VacancyStatusFilter[] | undefined,
	search: string | undefined,
	limit: number,
	searchId?: string,
	board?: BoardKind,
) {
	const sorted = statuses?.length ? [...statuses].sort() : null;
	return [
		...allVacanciesQueryKey,
		{
			statuses: sorted,
			search: search || null,
			limit,
			searchId: searchId ?? null,
			board: board ?? null,
		},
	];
}

export function createAllVacanciesQuery(
	getStatuses: () => readonly VacancyStatusFilter[] | undefined,
	getSearch: () => string | undefined,
	getLimit: () => number,
	getSearchId?: () => string | undefined,
	getBoard?: () => BoardKind | undefined,
	getQueryClient?: () => QueryClient,
) {
	return createQuery<VacancyListPage>(() => {
		const search = getSearch()?.trim() || undefined;
		const statuses = getStatuses()?.length ? getStatuses() : undefined;
		const searchId = getSearchId?.();
		const board = getBoard?.();
		return {
			queryKey: allVacanciesPageQueryKey(
				statuses,
				search,
				getLimit(),
				searchId,
				board,
			),
			queryFn: () =>
				API.vacancies.listAll({
					statuses,
					search,
					limit: getLimit(),
					searchId,
					board,
				}),
			placeholderData: keepPreviousData,
			staleTime: 30_000,
		};
	}, getQueryClient);
}

export function invalidateAllVacancies(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: allVacanciesQueryKey });
}
