import { API } from "$lib/api/client";
import { allVacanciesQueryKey } from "$lib/queries/all_vacancies";
import { summaryQueryKey } from "$lib/queries/summary";
import { vacanciesQueryKey } from "$lib/queries/vacancies";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createApplicationsActions(queryClient: QueryClient) {
	return {
		retryErrored: createMutation(() => ({
			mutationFn: async () => {
				return API.applications.retryErrored();
			},
			onSuccess() {
				queryClient.invalidateQueries({ queryKey: vacanciesQueryKey });
				queryClient.invalidateQueries({ queryKey: allVacanciesQueryKey });
				queryClient.invalidateQueries({ queryKey: summaryQueryKey });
			},
		})),
	};
}
