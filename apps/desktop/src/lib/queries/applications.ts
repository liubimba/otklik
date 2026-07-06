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
 * States for which the backend actually changes letter body / letters
 * history / reason during the transition into that state. Only these
 * warrant a refetch — intermediate ones (letter_pending, letter_sending)
 * flip status but leave latest_letter and letters_count untouched.
 *
 * Filtering here matters at perf level: during an auto-submit burst,
 * one vacancy fires 4-6 transitions in <2 s. Invalidating on every
 * event triggered 8-12 refetches per vacancy, which stormed the query
 * cache and the backend. See `PERF_BASELINE.md` scenario 1.
 */
const LETTER_CHANGING_STATES = new Set<ProcessingState>([
	"letter_ready",
	"letter_sent",
	"error",
	"skipped",
]);

/**
 * Handle a WS application_event.
 *
 * The event carries only `status` and `reason` — never letter body or
 * version counts. Behaviour depends on the status:
 *
 * 1. **Cache empty** → invalidate applicationQueryKey. The next observer
 *    will refetch the authoritative state from `/application`. This is
 *    the recovery path for a sheet opened before the Application was
 *    created in the DB (initial GET 404'd).
 *
 * 2. **Cache populated + intermediate status** (letter_pending,
 *    letter_sending) → merge status/reason only. No refetch: those
 *    transitions don't change letter body or history on the backend.
 *
 * 3. **Cache populated + letter-changing status** (letter_ready,
 *    letter_sent, error, skipped) → merge for immediate UI update, then
 *    invalidate both queries so latest_letter and the History tab pick
 *    up fresh data. Merge alone wouldn't help — the event carries
 *    neither letter body nor version count.
 */
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
		};
		queryClient.setQueryData(key, next);
		if (isLetterChanging) {
			queryClient.invalidateQueries({ queryKey: key });
			queryClient.invalidateQueries({ queryKey: historyKey });
		}
		return;
	}
	// Empty cache: always refetch the application (sheet opened before
	// the Application existed in the DB). History is only worth
	// invalidating if the state can actually add letter versions —
	// otherwise it stays a spurious refetch during intermediate ticks.
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
