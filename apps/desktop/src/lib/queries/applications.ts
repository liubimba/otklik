import { API } from "$lib/api/client";
import type {
	ApplicationDetail,
	ApplicationEvent,
	CoverLetter,
} from "$lib/api/types";
import { createQuery, type QueryClient } from "@tanstack/svelte-query";

export const applicationQueryKey = (vacancyId: number) =>
	["application", vacancyId] as const;

export const coverLettersHistoryQueryKey = (vacancyId: number) =>
	["cover-letters", vacancyId] as const;

/**
 * Combined application state: status + latest_letter + letters_count in one hit.
 * Replaces the old triple (status / cover_letter / cover_letters) — server
 * now returns the compound shape.
 */
export function createApplicationQuery(getVacancyId: () => number | null) {
	return createQuery<ApplicationDetail | null>(() => {
		const id = getVacancyId();
		return {
			queryKey: applicationQueryKey(id ?? -1),
			queryFn: () => API.application.get(id ?? -1),
			enabled: id !== null,
			staleTime: Number.POSITIVE_INFINITY,
		};
	});
}

/**
 * Merge a WS application_event into the cached ApplicationDetail without
 * clobbering the latest_letter fields — the event carries only status/reason.
 */
export function applyApplicationEvent(
	queryClient: QueryClient,
	event: ApplicationEvent,
) {
	queryClient.setQueryData<ApplicationDetail | null>(
		applicationQueryKey(event.data.vacancy_id),
		(prev) => {
			if (prev == null) return prev ?? null;
			return {
				...prev,
				status: event.data.status,
				reason: event.data.reason,
			};
		},
	);
}

export function createCoverLettersHistoryQuery(
	getVacancyId: () => number | null,
) {
	return createQuery<CoverLetter[]>(() => {
		const id = getVacancyId();
		return {
			queryKey: coverLettersHistoryQueryKey(id ?? -1),
			queryFn: () => API.application.letters(id ?? -1),
			enabled: id !== null,
			staleTime: Number.POSITIVE_INFINITY,
		};
	});
}
