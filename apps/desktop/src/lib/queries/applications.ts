import {
	getApplicationByVacancyId,
	getCoverLettersOfVacancyById,
	getLatestCoverLetterByVacancyId,
} from "$lib/api/client";
import type {
	ApplicationData,
	ApplicationEvent,
	CoverLetter,
} from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const applicationStatusQueryKey = (vacancyId: number) =>
	["application-status", vacancyId] as const;
export const latestCoverLetterQueryKey = (vacancyId: number) =>
	["latest-cover-letter", vacancyId] as const;
export const coverLettersHistoryQueryKey = (vacancyId: number) =>
	["cover-letters", vacancyId] as const;

export function createApplicationStatusQuery(
	getVacancyId: () => number | null,
) {
	return createQuery<ApplicationData | null>(() => {
		const id = getVacancyId();
		return {
			queryKey: applicationStatusQueryKey(id ?? -1),
			queryFn: () => getApplicationByVacancyId(id ?? -1),
			enabled: id !== null,
			staleTime: Number.POSITIVE_INFINITY,
		};
	});
}

export function applyApplicationStatus(
	queryClient: QueryClient,
	event: ApplicationEvent,
) {
	queryClient.setQueryData(
		applicationStatusQueryKey(event.data.vacancy_id),
		() => event.data,
	);
}

export function createLatestCoverLetterQuery(
	getVacancyId: () => number | null,
) {
	return createQuery<CoverLetter | null>(() => {
		const id = getVacancyId();
		return {
			queryKey: latestCoverLetterQueryKey(id ?? -1),
			queryFn: () => getLatestCoverLetterByVacancyId(id ?? -1),
			enabled: id !== null,
			staleTime: Number.POSITIVE_INFINITY,
		};
	});
}

export function createCoverLettersHistoryQuery(
	getVacancyId: () => number | null,
) {
	return createQuery<CoverLetter[]>(() => {
		const id = getVacancyId();
		return {
			queryKey: coverLettersHistoryQueryKey(id ?? -1),
			queryFn: () => getCoverLettersOfVacancyById(id ?? -1),
			enabled: id !== null,
			staleTime: Number.POSITIVE_INFINITY,
		};
	});
}
