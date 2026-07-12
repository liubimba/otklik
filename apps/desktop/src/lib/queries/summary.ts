import { API } from "$lib/api/client";
import type { ApplicationsSummary, SummaryScope } from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

/** Prefix key — invalidating it sweeps every scope at once. */
export const summaryQueryKey = ["applications-summary"] as const;

export function summaryScopeQueryKey(scope: SummaryScope) {
	return [...summaryQueryKey, scope] as const;
}

/**
 * Счётчик «требует внимания» для сайдбара. Одно число, а не список: сайдбар
 * висит на каждом экране, и вешать его на выдачу всех вакансий значило бы
 * платить самым тяжёлым запросом за одну цифру.
 *
 * Scope повторяет словарь GET /vacancies/: `"all"` — по всей базе, это то, что
 * показывают «Все вакансии»; `"latest"` — только текущий поиск, а это ровно то,
 * и только то, что показывает «Очередь вакансий». Каждый scope получает свой
 * ключ кэша — иначе два ряда сайдбара дрались бы за одну запись.
 */
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

/**
 * Событие смены статуса заявки не несёт в себе новое количество, а считать его
 * на клиенте значило бы дублировать определение «требует внимания», которое
 * живёт в бэкенде. Поэтому — инвалидация по префиксу: оба scope разом, один
 * COUNT на каждый вместо перезагрузки списка.
 */
export function invalidateSummary(queryClient: QueryClient): void {
	queryClient.invalidateQueries({ queryKey: summaryQueryKey });
}
