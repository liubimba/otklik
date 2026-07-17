import { API } from "$lib/api/client";
import { TERMINAL_SEARCH_STATUSES } from "$lib/api/types";
import type { SearchEvent, Vacancy, VacancyEvent } from "$lib/api/types";
import {
	type QueryClient,
	createQuery,
	useQueryClient,
} from "@tanstack/svelte-query";

export const vacanciesQueryKey = ["vacancies"] as const;

export function vacancyQueryKey(vacancyId: number) {
	return ["vacancy", vacancyId] as const;
}

export function createVacanciesQuery() {
	return createQuery<Vacancy[]>(() => ({
		queryKey: vacanciesQueryKey,
		queryFn: () => API.vacancies.list(),
		staleTime: 30_000,
	}));
}

export function createVacancyQuery(getVacancyId: () => number | null) {
	const queryClient = useQueryClient();
	return createQuery<Vacancy | null>(() => {
		const vacancyId = getVacancyId();
		return {
			queryKey: vacancyQueryKey(vacancyId ?? -1),
			queryFn: () => API.vacancies.get(vacancyId ?? -1),
			enabled: vacancyId !== null,
			staleTime: Number.POSITIVE_INFINITY,
			initialData: () =>
				vacancyId === null
					? undefined
					: queryClient
							.getQueryData<Vacancy[]>(vacanciesQueryKey)
							?.find((vacancy) => vacancy.id === vacancyId),
		};
	});
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
