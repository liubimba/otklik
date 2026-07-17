import { API } from "$lib/api/client";
import type { ApplicationsSummary, SummaryScope } from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const summaryQueryKey = ["applications-summary"] as const;

export function summaryScopeQueryKey(scope: SummaryScope) {
	return [...summaryQueryKey, scope] as const;
}

export function createSummaryQuery(
	scope: SummaryScope,
	getQueryClient?: () => QueryClient,
) {
	return createQuery<ApplicationsSummary>(
		() => ({
			queryKey: summaryScopeQueryKey(scope),
			queryFn: () => API.applications.summary(scope),
			staleTime: 30_000,
		}),
		getQueryClient,
	);
}

export function invalidateSummary(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: summaryQueryKey });
}
