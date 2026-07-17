import { API } from "$lib/api/client";
import type {
	ApplicationDetail,
	ApplicationEvent,
	ChatMessage,
	CoverLetter,
	ProcessingState,
} from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const applicationQueryKey = (vacancyId: number) =>
	["application", vacancyId] as const;

export const coverLettersHistoryQueryKey = (vacancyId: number) =>
	["cover-letters", vacancyId] as const;

export const chatMessagesQueryKey = (vacancyId: number) =>
	["chat", vacancyId] as const;

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

const LETTER_CHANGING_STATES = new Set<ProcessingState>([
	"letter_ready",
	"letter_sent",
	"error",
	"skipped",
]);

export function applyApplicationEvent(
	queryClient: QueryClient,
	event: ApplicationEvent,
) {
	const key = applicationQueryKey(event.data.vacancy_id);
	const historyKey = coverLettersHistoryQueryKey(event.data.vacancy_id);
	const prev = queryClient.getQueryData<ApplicationDetail | null>(key);
	const isLetterChanging = LETTER_CHANGING_STATES.has(event.data.status);
	if (prev != null) {
		const next: ApplicationDetail = {
			...prev,
			status: event.data.status,
			reason: event.data.reason,
			error_domain: event.data.error_domain,
		};
		queryClient.setQueryData(key, next);
		if (isLetterChanging) {
			queryClient.invalidateQueries({ queryKey: key });
			queryClient.invalidateQueries({ queryKey: historyKey });
		}
		return;
	}
	queryClient.invalidateQueries({ queryKey: key });
	if (isLetterChanging) {
		queryClient.invalidateQueries({ queryKey: historyKey });
	}
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

export function createChatMessagesQuery(getVacancyId: () => number | null) {
	return createQuery<ChatMessage[]>(() => {
		const id = getVacancyId();
		return {
			queryKey: chatMessagesQueryKey(id ?? -1),
			queryFn: () => API.application.chat.list(id ?? -1),
			enabled: id !== null,
			staleTime: Number.POSITIVE_INFINITY,
		};
	});
}
