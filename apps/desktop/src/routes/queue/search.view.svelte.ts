import type { createActions } from "$lib/actions";
import type { query } from "$lib/queries";
import { store } from "$lib/stores";
import { Utils } from "$lib/utils/utils";
import type { SearchPageViewModel } from "./search.view_model.svelte";

type SearchQuery = ReturnType<typeof query.search.vacancies.create>;
type Actions = ReturnType<typeof createActions>;

export function createSearchPageView(
	searchQuery: SearchQuery,
	actions: Actions,
	model: SearchPageViewModel,
) {
	return {
		search: {
			filter: {
				start: () => {
					if (searchQuery.data) {
						model.dialog.search.filter.active = true;
						return;
					}
					if (store.search.filter.canOpen) {
						actions.search.filter.open.mutateAsync();
					}
				},
				confirm: async () => {
					if (store.search.filter.canConfirm) {
						if (store.search.filter.sessionId === null) {
							throw new Error();
						}
						actions.search.filter.confirm
							.mutateAsync()
							.then(async (response) => {
								actions.search.vacancies.start.mutateAsync({
									url: response.url,
									maxPages: Utils.numeric.parseOptional(
										model.search.filter.maxPages,
									),
									maxVacancies: Utils.numeric.parseOptional(
										model.search.filter.maxVacancies,
									),
								});
							});
					}
				},
				cancel: () => {
					if (store.search.filter.canCancel) {
						if (store.search.filter.sessionId === null) {
							throw new Error();
						}
						actions.search.filter.cancel.mutateAsync({
							sessionId: store.search.filter.sessionId,
						});
					}
				},
				dismissError: () => {
					model.search.filter.maxPages = "";
					model.search.filter.maxVacancies = "";
					store.search.filter.clearError();
				},
				dialog: {
					replace: async () => {
						if (!searchQuery.data) {
							model.dialog.search.filter.active = false;
							return;
						}
						try {
							await actions.search.vacancies.cancel.mutateAsync({
								searchId: searchQuery.data.search_id,
							});
							await actions.search.filter.open.mutateAsync();
						} catch (error) {}
						model.dialog.search.filter.active = false;
					},
				},
			},
		},
	};
}
