import type { createActions } from "$lib/actions";
import * as m from "$lib/paraglide/messages";
import type { query } from "$lib/queries";
import { store } from "$lib/stores";
import { Utils } from "$lib/utils/utils";
import { toast } from "svelte-sonner";
import type { SearchPageViewModel } from "./search.view_model.svelte";

function describeError(error: unknown): string {
	return error instanceof Error ? error.message : "unknown error";
}

type SearchQuery = ReturnType<typeof query.search.vacancies.create>;
type Actions = ReturnType<typeof createActions>;

export function createSearchPageView(
	searchQuery: SearchQuery,
	actions: Actions,
	model: SearchPageViewModel,
) {
	return {
		search: {
			vacancies: {
				pauseResume: () => {
					const data = searchQuery.data;
					if (!data) return;
					if (model.search.vacancies.paused) {
						actions.search.vacancies.resume
							.mutateAsync({ searchId: data.search_id })
							.catch((error) =>
								toast.error(
									m.queue_resume_failed({ error: describeError(error) }),
								),
							);
					} else {
						actions.search.vacancies.pause
							.mutateAsync({ searchId: data.search_id })
							.catch((error) =>
								toast.error(
									m.queue_pause_failed({ error: describeError(error) }),
								),
							);
					}
				},
			},
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
		auto: {
			toggleGenerate: (value: boolean) => {
				actions.settings.updateUser
					.mutateAsync({ user: { auto_generate: value } })
					.catch((error) =>
						toast.error(
							m.queue_auto_save_failed({ error: describeError(error) }),
						),
					);
			},
			toggleSubmit: (value: boolean) => {
				actions.settings.updateUser
					.mutateAsync({ user: { auto_submit: value } })
					.catch((error) =>
						toast.error(
							m.queue_auto_save_failed({ error: describeError(error) }),
						),
					);
			},
		},
		applications: {
			retryErrored: () => {
				actions.applications.retryErrored
					.mutateAsync()
					.then((result) =>
						toast.success(m.queue_retry_success({ count: result.retried })),
					)
					.catch((error) =>
						toast.error(m.queue_retry_failed({ error: describeError(error) })),
					);
			},
		},
	};
}
