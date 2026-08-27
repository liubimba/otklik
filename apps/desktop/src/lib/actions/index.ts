import { createAICoverLetterActions } from "$lib/actions/ai";
import { createApplicationsActions } from "$lib/actions/applications";
import { createLetterReviewActions } from "$lib/actions/letter-review";
import { createPreviewActions } from "$lib/actions/preview";
import { createSettingsActions } from "$lib/actions/settings";
import { createSourcesActions } from "$lib/actions/sources";
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
		sources: createSourcesActions(queryClient),
		preview: createPreviewActions(queryClient),
		settings: createSettingsActions(queryClient),
		applications: createApplicationsActions(queryClient),
	};
}
