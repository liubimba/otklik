import {
	allVacanciesQueryKey,
	createAllVacanciesQuery,
	invalidateAllVacancies,
} from "$lib/queries/all_vacancies";
import {
	applicationQueryKey,
	applyApplicationEvent,
	coverLettersHistoryQueryKey,
	createApplicationQuery,
	createCoverLettersHistoryQuery,
} from "$lib/queries/applications";
import {
	applyAuthEvent,
	authQueryKey,
	createAuthQuery,
} from "$lib/queries/auth";
import {
	applyCurrentSearchEvent,
	createCurrentSearchQuery,
} from "$lib/queries/search";
import {
	applySearchHistoryEvent,
	createSearchHistoryQuery,
	searchHistoryQueryKey,
} from "$lib/queries/search_history";
import { createSettingsQuery, settingsQueryKey } from "$lib/queries/settings";
import {
	applyVacancyEvent,
	createVacanciesQuery,
	vacanciesQueryKey,
} from "$lib/queries/vacancies";

export const query = {
	search: {
		vacancies: {
			create: createCurrentSearchQuery,
			apply: applyCurrentSearchEvent,
		},
		history: {
			key: searchHistoryQueryKey,
			create: createSearchHistoryQuery,
			apply: applySearchHistoryEvent,
		},
	},
	vacancies: {
		key: vacanciesQueryKey,
		create: createVacanciesQuery,
		apply: applyVacancyEvent,
	},
	all_vacancies: {
		key: allVacanciesQueryKey,
		create: createAllVacanciesQuery,
		invalidate: invalidateAllVacancies,
	},
	settings: {
		key: settingsQueryKey,
		create: createSettingsQuery,
	},
	auth: {
		key: authQueryKey,
		create: createAuthQuery,
		apply: applyAuthEvent,
	},
	application: {
		key: applicationQueryKey,
		create: createApplicationQuery,
		apply: applyApplicationEvent,
	},
	cover_letter: {
		history: {
			key: coverLettersHistoryQueryKey,
			create: createCoverLettersHistoryQuery,
		},
	},
};

export type Query = typeof query;
