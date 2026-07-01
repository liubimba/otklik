import { API } from "$lib/api/client";
import type { SearchData } from "$lib/api/types";
import { currentSearchQueryKey } from "$lib/queries/search";
import { vacanciesQueryKey } from "$lib/queries/vacancies";
import type { SearchFilterStore } from "$lib/stores/search_filter.store.svelte";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createSearchVacanciesActions(queryClient: QueryClient) {
	return {
		start: createMutation(() => ({
			mutationFn: async (params: {
				url: string;
				maxPages?: number;
				maxVacancies?: number;
			}) => {
				return API.search.parse.start(
					params.url,
					params.maxPages,
					params.maxVacancies,
				);
			},
			onSuccess(search: SearchData) {
				queryClient.setQueryData(currentSearchQueryKey, search);
				queryClient.invalidateQueries({ queryKey: vacanciesQueryKey });
			},
		})),
		cancel: createMutation(() => ({
			mutationFn: async (params: {
				searchId: string;
			}) => {
				return API.search.parse.cancel(params.searchId);
			},
		})),
	};
}

export function createSearchFilterActions(
	queryClient: QueryClient,
	store: SearchFilterStore,
) {
	return {
		open: createMutation(() => ({
			mutationFn: async () => {
				if (store.canOpen) {
					store.opening();
					store.clearError();
					return API.search.filter.open();
				}
				throw new Error("Search filter session cannot be open");
			},
			onSuccess(response) {
				if (response) {
					store.opened(response.session_id);
				} else {
					throw new Error("No session ID returned");
				}
			},
			onError(error) {
				store.failed(`${error.message}. State: ${store.state.status}`);
			},
		})),
		cancel: createMutation(() => ({
			mutationFn: async (params: { sessionId: string }) => {
				if (store.canCancel) {
					if (!store.sessionId) {
						throw new Error("Session ID undefined");
					}
					store.canceling();
					return API.search.filter.cancel(store.sessionId);
				}
				throw new Error("Search filter session cannot be canceled");
			},
			onSuccess() {
				store.canceled();
				queryClient.setQueryData(currentSearchQueryKey, null);
				queryClient.invalidateQueries({
					queryKey: vacanciesQueryKey,
				});
			},
		})),
		confirm: createMutation(() => ({
			mutationFn: async () => {
				if (store.canConfirm) {
					if (!store.sessionId) {
						throw new Error("Session ID undefined");
					}
					store.confirming();
					return API.search.filter.confirm(store.sessionId);
				}
				throw new Error("Search filter session cannot be confirmed");
			},
			onSuccess() {
				store.confirmed();
			},
			onError(error) {
				store.failed(error.message);
			},
		})),
		dismissError: createMutation(() => ({
			mutationFn: async (params: {}) => {
				store.clearError();
			},
		})),
	};
}

export function createAuthActions(queryClient: QueryClient) {
	return {
		authenticate: createMutation(() => ({
			mutationFn: async () => {
				return API.auth.signIn();
			},
			onSuccess(response) {},
		})),
		cancel: createMutation(() => ({
			mutationFn: async () => {
				return API.auth.signInCancel();
			},
		})),
		unauthorize: createMutation(() => ({
			mutationFn: async () => {
				return API.auth.signOut();
			},
		})),
	};
}
