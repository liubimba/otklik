import { API } from "$lib/api/client";
import {
	applicationQueryKey,
	coverLettersHistoryQueryKey,
} from "$lib/queries/applications";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

async function invalidate(queryClient: QueryClient, vacancyId: number) {
	await Promise.all([
		queryClient.invalidateQueries({
			queryKey: applicationQueryKey(vacancyId),
		}),
		queryClient.invalidateQueries({
			queryKey: coverLettersHistoryQueryKey(vacancyId),
		}),
	]);
}

/**
 * All mutations map 1:1 to the new /vacancies/{id}/application/* endpoints.
 * `generate` is now a single call — the server auto-creates the Application if
 * needed. `submit` accepts an optional draft text so we no longer save then
 * submit in two hops.
 */
export function createLetterReviewActions(queryClient: QueryClient) {
	return {
		generate: createMutation(() => ({
			mutationFn: (vacancyId: number) => API.application.generate(vacancyId),
			onSuccess: (_, vacancyId) => invalidate(queryClient, vacancyId),
		})),
		save: createMutation(() => ({
			mutationFn: (params: { vacancyId: number; text: string }) =>
				API.application.save(params.vacancyId, params.text),
			onSuccess: (_, params) => invalidate(queryClient, params.vacancyId),
		})),
		submit: createMutation(() => ({
			mutationFn: (params: { vacancyId: number; text?: string }) =>
				API.application.submit(params.vacancyId, params.text),
			onSuccess: (_, params) => invalidate(queryClient, params.vacancyId),
		})),
		skip: createMutation(() => ({
			mutationFn: (vacancyId: number) => API.application.skip(vacancyId),
			onSuccess: (_, vacancyId) => invalidate(queryClient, vacancyId),
		})),
		retry: createMutation(() => ({
			mutationFn: (vacancyId: number) => API.application.retry(vacancyId),
			onSuccess: (_, vacancyId) => invalidate(queryClient, vacancyId),
		})),
	};
}
