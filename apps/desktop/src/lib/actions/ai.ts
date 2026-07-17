import { API } from "$lib/api/client";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createAICoverLetterActions(
	_queryClient: QueryClient,
	vacancyId: number,
) {
	return {
		generate: createMutation(() => ({
			mutationFn: async () => API.application.generate(vacancyId),
		})),
	};
}
