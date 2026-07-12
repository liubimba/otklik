import { API } from "$lib/api/client";
import type { ApplicationsSummary } from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const summaryQueryKey = ["applications-summary"] as const;

/**
 * Счётчик «требует внимания» для сайдбара. Одно число, а не список: сайдбар
 * висит на каждом экране, и вешать его на выдачу всех вакансий значило бы
 * платить самым тяжёлым запросом за одну цифру.
 */
export function createSummaryQuery(getQueryClient?: () => QueryClient) {
	return createQuery<ApplicationsSummary>(
		() => ({
			queryKey: summaryQueryKey,
			queryFn: () => API.applications.summary(),
			staleTime: 30_000,
		}),
		getQueryClient,
	);
}

/**
 * Событие смены статуса заявки не несёт в себе новое количество, а считать его
 * на клиенте значило бы дублировать определение «требует внимания», которое
 * живёт в бэкенде. Поэтому — инвалидация: один COUNT вместо перезагрузки списка.
 */
export function invalidateSummary(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: summaryQueryKey });
}
