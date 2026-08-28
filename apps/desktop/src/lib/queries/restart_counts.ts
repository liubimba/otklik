import { API } from "$lib/api/client";
import type { RestartCounts } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const restartCountsQueryKey = ["restart-counts"] as const;

export function createRestartCountsQuery() {
	return createQuery<RestartCounts>(() => ({
		queryKey: restartCountsQueryKey,
		queryFn: API.applications.restartCounts,
		staleTime: 30_000,
	}));
}
