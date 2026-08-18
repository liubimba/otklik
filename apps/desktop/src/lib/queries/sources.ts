import { API } from "$lib/api/client";
import type { ContextSource } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const sourcesQueryKey = ["context-sources"] as const;

export function createSourcesQuery() {
	return createQuery<ContextSource[]>(() => ({
		queryKey: sourcesQueryKey,
		queryFn: API.sources.list,
		staleTime: Number.POSITIVE_INFINITY,
	}));
}
