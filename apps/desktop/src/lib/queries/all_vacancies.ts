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
) {
	const sorted = statuses?.length ? [...statuses].sort() : null;
	return [
		...allVacanciesQueryKey,
		{ statuses: sorted, search: search || null, limit },
	];
}

export function createAllVacanciesQuery(
	getStatuses: () => readonly VacancyStatusFilter[] | undefined,
	getSearch: () => string | undefined,
	getLimit: () => number,
	getQueryClient?: () => QueryClient,
) {
	return createQuery<VacancyListPage>(() => {
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

export function invalidateAllVacancies(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: allVacanciesQueryKey });
}
