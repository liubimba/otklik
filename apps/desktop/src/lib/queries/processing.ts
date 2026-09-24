import { API } from "$lib/api/client";
import type { ProcessingStatus } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const processingQueryKey = ["processing"] as const;

export function createProcessingQuery() {
	return createQuery<ProcessingStatus>(() => ({
		queryKey: processingQueryKey,
		queryFn: API.processing.status,
	}));
}
