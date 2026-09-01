import { API } from "$lib/api/client";
import type { VacancyListPage, VacancyStatusFilter } from "$lib/api/types";
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
) {
	const sorted = statuses?.length ? [...statuses].sort() : null;
	return [
		...allVacanciesQueryKey,
		{
			statuses: sorted,
			search: search || null,
			limit,
			searchId: searchId ?? null,
		},
	];
}

export function createAllVacanciesQuery(
	getStatuses: () => readonly VacancyStatusFilter[] | undefined,
	getSearch: () => string | undefined,
	getLimit: () => number,
	getSearchId?: () => string | undefined,
	getQueryClient?: () => QueryClient,
) {
	return createQuery<VacancyListPage>(() => {
		const search = getSearch()?.trim() || undefined;
		const statuses = getStatuses()?.length ? getStatuses() : undefined;
		const searchId = getSearchId?.();
		return {
			queryKey: allVacanciesPageQueryKey(
				statuses,
				search,
				getLimit(),
				searchId,
			),
			queryFn: () =>
				API.vacancies.listAll({
					statuses,
					search,
					limit: getLimit(),
					searchId,
				}),
			placeholderData: keepPreviousData,
			staleTime: 30_000,
		};
	}, getQueryClient);
}

export function invalidateAllVacancies(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: allVacanciesQueryKey });
}
