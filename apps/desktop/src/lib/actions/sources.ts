import { API } from "$lib/api/client";
import type { ContextSourceWrite } from "$lib/api/types";
import { sourcesQueryKey } from "$lib/queries/sources";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export const createSourcesActions = (queryClient: QueryClient) => {
	const invalidate = () => {
		queryClient.invalidateQueries({ queryKey: sourcesQueryKey });
	};

	return {
		add: createMutation(() => ({
			mutationFn: async (body: ContextSourceWrite) => API.sources.create(body),
			onSuccess() {
				invalidate();
			},
		})),
		update: createMutation(() => ({
			mutationFn: async (params: { id: number; body: ContextSourceWrite }) =>
				API.sources.update(params.id, params.body),
			onSuccess() {
				invalidate();
			},
		})),
		remove: createMutation(() => ({
			mutationFn: async (id: number) => API.sources.remove(id),
			onSuccess() {
				invalidate();
			},
		})),
		refresh: createMutation(() => ({
			mutationFn: async (id: number) => API.sources.refresh(id),
			onSuccess() {
				invalidate();
			},
		})),
		refreshAll: createMutation(() => ({
			mutationFn: async () => API.sources.refreshAll(),
			onSuccess() {
				invalidate();
			},
		})),
	};
};
