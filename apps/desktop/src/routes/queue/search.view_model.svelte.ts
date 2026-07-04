import * as m from "$lib/paraglide/messages";
import type { query } from "$lib/queries";
import { store } from "$lib/stores";

type SearchQuery = ReturnType<typeof query.search.vacancies.create>;

class SearchFilterModel {
	maxPages = $state<string>("");
	maxVacancies = $state<string>("");
	readonly inactive = $derived(
		store.search.filter.state.status === "idle" ||
			store.search.filter.state.status === "error",
	);
}

class SearchVacanciesModel {
	readonly inFlight: boolean;
	readonly status: string;

	constructor(searchQuery: SearchQuery) {
		this.inFlight = $derived(
			searchQuery.data?.status === "running" ||
				searchQuery.data?.status === "pending",
		);
		this.status = $derived.by(() => {
			const data = searchQuery.data;
			if (!data) return m.status_unknown();
			switch (data.status) {
				case "pending":
					return m.status_pending();
				case "running":
					return m.status_running();
				case "canceled":
					return m.status_canceled();
				case "exited":
					return m.status_exited();
				case "failed":
					return m.status_failed();
				case "interrupted":
					return m.status_interrupted();
				default:
					return m.status_unknown();
			}
		});
	}
}

class SearchView_modelSvelte {
	readonly filter = new SearchFilterModel();
	readonly vacancies: SearchVacanciesModel;

	constructor(searchQuery: SearchQuery) {
		this.vacancies = new SearchVacanciesModel(searchQuery);
	}
}

class DialogSearchFilterModel {
	active = $state<boolean>(false);
}

class DialogSearchModel {
	readonly filter = new DialogSearchFilterModel();
}

class DialogModel {
	readonly search = new DialogSearchModel();
}

export class SearchPageViewModel {
	readonly search: SearchView_modelSvelte;
	readonly dialog = new DialogModel();

	constructor(searchQuery: SearchQuery) {
		this.search = new SearchView_modelSvelte(searchQuery);
	}
}

export function createSearchPageViewModel(searchQuery: SearchQuery) {
	return new SearchPageViewModel(searchQuery);
}
