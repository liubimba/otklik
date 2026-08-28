import { API } from "$lib/api/client";
import { allVacanciesQueryKey } from "$lib/queries/all_vacancies";
import { restartCountsQueryKey } from "$lib/queries/restart_counts";
import { summaryQueryKey } from "$lib/queries/summary";
import { vacanciesQueryKey } from "$lib/queries/vacancies";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

function invalidateQueues(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: vacanciesQueryKey });
	queryClient.invalidateQueries({ queryKey: allVacanciesQueryKey });
	queryClient.invalidateQueries({ queryKey: summaryQueryKey });
	queryClient.invalidateQueries({ queryKey: restartCountsQueryKey });
}

export function createApplicationsActions(queryClient: QueryClient) {
	return {
		restartGeneration: createMutation(() => ({
			mutationFn: async () => {
				return API.applications.restartGeneration();
			},
			onSuccess() {
				invalidateQueues(queryClient);
			},
		})),
		restartSubmission: createMutation(() => ({
			mutationFn: async () => {
				return API.applications.restartSubmission();
			},
			onSuccess() {
				invalidateQueues(queryClient);
			},
		})),
	};
}
