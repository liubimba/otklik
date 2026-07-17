import { API } from "$lib/api/client";
import { applicationQueryKey } from "$lib/queries/applications";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export const createVacanciesActions = (
	queryClient: QueryClient,
	vacancyId: number,
) => {
	const setApplication = (data: unknown) => {
		queryClient.setQueryData(applicationQueryKey(vacancyId), data);
	};

	return {
		submit: createMutation(() => ({
			mutationFn: async (params: { text?: string } = {}) =>
				API.application.submit(vacancyId, params.text),
			onSuccess(response) {
				setApplication(response);
			},
		})),
		save: createMutation(() => ({
			mutationFn: async (params: { text: string }) =>
				API.application.save(vacancyId, params.text),
			onSuccess() {
				queryClient.invalidateQueries({
					queryKey: applicationQueryKey(vacancyId),
				});
			},
		})),
		generate: createMutation(() => ({
			mutationFn: async () => API.application.generate(vacancyId),
			onSuccess() {
				queryClient.invalidateQueries({
					queryKey: applicationQueryKey(vacancyId),
				});
			},
		})),
		retry: createMutation(() => ({
			mutationFn: async () => API.application.retry(vacancyId),
			onSuccess(response) {
				setApplication(response);
			},
		})),
		skip: createMutation(() => ({
			mutationFn: async () => API.application.skip(vacancyId),
			onSuccess(response) {
				setApplication(response);
			},
		})),
	};
};
