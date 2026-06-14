import { getVacancies } from "$lib/api/client";
import { TERMINAL_SEARCH_STATUSES } from "$lib/api/types";
import type { SearchEvent, Vacancy, VacancyEvent } from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const vacanciesQueryKey = ["vacancies"] as const;

export function createVacanciesQuery() {
	return createQuery<Vacancy[]>(() => ({
		queryKey: vacanciesQueryKey,
		queryFn: getVacancies,
		staleTime: 30_000,
	}));
}

export function applyVacancyEvent(
	queryClient: QueryClient,
	event: VacancyEvent,
): void {
	queryClient.setQueryData<Vacancy[]>(vacanciesQueryKey, (old) => [
		event.data,
		...(old ?? []).filter((v) => v.id !== event.data.id),
	]);
}

export function applySearchEvent(
	queryClient: QueryClient,
	event: SearchEvent,
): void {
	if (TERMINAL_SEARCH_STATUSES.has(event.data.status)) {
		queryClient.invalidateQueries({ queryKey: vacanciesQueryKey });
	}
}
