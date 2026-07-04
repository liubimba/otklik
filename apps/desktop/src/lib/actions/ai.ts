import { API } from "$lib/api/client";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

/**
 * AI generation is now folded into /vacancies/{id}/application/generate.
 * Kept as a stand-alone action factory for call sites that still ask for
 * `actions.ai.cover_letter(vacancyId).generate` explicitly.
 */
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
