import { createAICoverLetterActions } from "$lib/actions/ai";
import { createLetterReviewActions } from "$lib/actions/letter-review";
import { createVacanciesActions } from "$lib/actions/vacancies";
import { store } from "$lib/stores";
import type { QueryClient } from "@tanstack/svelte-query";
import {
	createAuthActions,
	createSearchFilterActions,
	createSearchVacanciesActions,
} from "../../routes/queue/search.actions.svelte";

export function createActions(queryClient: QueryClient) {
	return {
		search: {
			filter: createSearchFilterActions(queryClient, store.search.filter),
			vacancies: createSearchVacanciesActions(queryClient),
		},
		auth: createAuthActions(queryClient),
		ai: {
			cover_letter: (vacancyId: number) =>
				createAICoverLetterActions(queryClient, vacancyId),
		},
		vacancies: (vacancyId: number) =>
			createVacanciesActions(queryClient, vacancyId),
		letter: {
			review: createLetterReviewActions(queryClient),
		},
	};
}
