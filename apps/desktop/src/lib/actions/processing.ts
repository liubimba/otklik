import { API } from "$lib/api/client";
import type { ProcessingStatus } from "$lib/api/types";
import { processingQueryKey } from "$lib/queries/processing";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createProcessingActions(queryClient: QueryClient) {
	function patch(paused: boolean) {
		queryClient.setQueryData<ProcessingStatus>(processingQueryKey, (old) =>
			old ? { ...old, paused } : old,
		);
	}

	return {
		pause: createMutation(() => ({
			mutationFn: () => API.processing.pause(),
			onSuccess: () => patch(true),
		})),
		resume: createMutation(() => ({
			mutationFn: () => API.processing.resume(),
			onSuccess: () => patch(false),
		})),
		cancel: createMutation(() => ({
			mutationFn: () => API.processing.cancel(),
			onSuccess: (status: ProcessingStatus) => {
				queryClient.setQueryData(processingQueryKey, status);
			},
		})),
	};
}
