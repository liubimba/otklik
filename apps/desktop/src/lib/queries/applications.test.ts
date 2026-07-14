import type { ApplicationDetail, ApplicationEvent } from "$lib/api/types";
import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import {
	applicationQueryKey,
	applyApplicationEvent,
	coverLettersHistoryQueryKey,
} from "./applications";

/**
 * Minimal QueryClient stand-in: only setQueryData is exercised by the
 * function under test. Using a fake keeps the test focused on merge
 * semantics — no need for the real client's internal state.
 */
function makeFakeQueryClient(): {
	client: QueryClient;
	updater: {
		called: boolean;
		key: unknown;
		result: ApplicationDetail | null;
	};
	invalidations: unknown[];
	seed: (data: ApplicationDetail | null) => void;
} {
	let seeded: ApplicationDetail | null = null;
	const updater = {
		called: false,
		key: undefined as unknown,
		result: null as ApplicationDetail | null,
	};
	const invalidations: unknown[] = [];
	const client = {
		getQueryData: vi.fn(() => seeded),
		setQueryData: vi.fn(
			(
				key: unknown,
				valueOrUpdater:
					| ApplicationDetail
					| null
					| ((prev: ApplicationDetail | null) => ApplicationDetail | null),
			) => {
				updater.called = true;
				updater.key = key;
				updater.result =
					typeof valueOrUpdater === "function"
						? (
								valueOrUpdater as (
									prev: ApplicationDetail | null,
								) => ApplicationDetail | null
							)(seeded)
						: valueOrUpdater;
			},
		),
		invalidateQueries: vi.fn((params: { queryKey: unknown }) => {
			invalidations.push(params.queryKey);
			return Promise.resolve();
		}),
	} as unknown as QueryClient;
	return {
		client,
		updater,
		invalidations,
		seed(data) {
			seeded = data;
		},
	};
}

const baseDetail: ApplicationDetail = {
	vacancy_id: 1,
	application_id: 100,
	retry_count: 0,
	status: "letter_ready",
	reason: null,
	error_domain: null,
	created_at: "2026-07-01T10:00:00Z",
	updated_at: "2026-07-01T10:00:05Z",
	latest_letter: {
		text: "Existing letter",
		version: 3,
		created_at: "2026-07-01T10:00:05Z",
	},
	letters_count: 3,
};

function eventFor(
	vacancy_id: number,
	status: ApplicationDetail["status"],
	reason: string | null = null,
	error_domain: ApplicationDetail["error_domain"] = null,
): ApplicationEvent {
	return {
		type: "application_event",
		data: {
			vacancy_id,
			application_id: 100,
			status,
			reason,
			error_domain,
		},
	};
}

describe("applyApplicationEvent", () => {
	it("merges status and reason into the cached ApplicationDetail without clobbering letter fields", () => {
		const { client, updater, seed } = makeFakeQueryClient();
		seed(baseDetail);

		applyApplicationEvent(client, eventFor(1, "letter_sending", "captcha"));

		expect(updater.called).toBe(true);
		expect(updater.key).toEqual(applicationQueryKey(1));
		expect(updater.result).toEqual({
			...baseDetail,
			status: "letter_sending",
			reason: "captcha",
		});
		// Sanity: latest_letter and letters_count survive the merge.
		expect(updater.result?.latest_letter).toEqual(baseDetail.latest_letter);
		expect(updater.result?.letters_count).toBe(3);
	});

	// error_domain rides alongside reason so the viewmodel can tell an LLM
	// failure (FAIL) from an hh.ru submission failure (SUBMISSION_FAILED)
	// without guessing from the reason text — see
	// letter-review-sheet.viewmodel.svelte.ts.
	it("merges error_domain alongside reason", () => {
		const { client, updater, seed } = makeFakeQueryClient();
		seed(baseDetail);

		applyApplicationEvent(
			client,
			eventFor(1, "error", "verification timeout", "submission"),
		);

		expect(updater.result?.reason).toBe("verification timeout");
		expect(updater.result?.error_domain).toBe("submission");
	});

	it("also invalidates letter body + history so latest_letter and versions refresh", () => {
		/**
		 * Regression 2026-07-02 (second half): after the first fix let
		 * the sheet track status transitions, the letter textarea and
		 * the History tab still showed empty. Cause: the merge path
		 * only overwrote status/reason. If the first successful GET
		 * /application landed while the app was still in letter_pending
		 * (latest_letter=null, letters_count=0), the subsequent
		 * letter_ready → letter_sending → letter_sent events all
		 * merged over that stale record, so latest_letter stayed null
		 * and the separate coverLettersHistoryQuery was never
		 * invalidated at all.
		 *
		 * Fix: every event must invalidate both applicationQueryKey
		 * (to pull fresh latest_letter) and coverLettersHistoryQueryKey
		 * (to refresh the versions list).
		 */
		const { client, invalidations, seed } = makeFakeQueryClient();
		seed(baseDetail);

		applyApplicationEvent(client, eventFor(1, "letter_sent"));

		expect(invalidations).toEqual(
			expect.arrayContaining([
				applicationQueryKey(1),
				coverLettersHistoryQueryKey(1),
			]),
		);
	});

	it("invalidates the query when the cache is empty so the next mount refetches fresh state", () => {
		/**
		 * Regression: a user opened the letter-review-sheet for a
		 * vacancy the AutoApplyListener had not yet processed. The
		 * first GET /application 404'd, the query cached that failure,
		 * and subsequent application_event WS messages (letter_pending
		 * → letter_ready → letter_sending → letter_sent) were silently
		 * dropped by this function because prev == null. The UI then
		 * showed the "parsed" fallback with a live Generate button —
		 * clicking it produced a 409 (state machine had already
		 * moved to LETTER_SENT). Reported 2026-07-02.
		 *
		 * Fix: on an empty cache, force an invalidateQueries so the
		 * next observer refetches the current status from the backend.
		 */
		const { client, updater, invalidations, seed } = makeFakeQueryClient();
		seed(null);

		applyApplicationEvent(client, eventFor(1, "letter_sent"));

		expect(updater.called).toBe(false);
		expect(invalidations).toEqual(
			expect.arrayContaining([
				applicationQueryKey(1),
				coverLettersHistoryQueryKey(1),
			]),
		);
	});

	it("routes updates by vacancy_id in the query key", () => {
		const { client, updater, seed } = makeFakeQueryClient();
		// Merge path only runs when a cached entry exists — otherwise the
		// function invalidates instead of writing. Seed so we hit the
		// setQueryData branch that this test cares about.
		seed({ ...baseDetail, vacancy_id: 42 });

		applyApplicationEvent(client, eventFor(42, "skipped"));

		expect(updater.key).toEqual(applicationQueryKey(42));
	});

	// Perf-driven filtering: intermediate states (letter_pending,
	// letter_sending) don't change latest_letter or letters_count on the
	// backend, so invalidating them just multiplies refetches during an
	// auto-submit burst without changing any UI. Only status/reason
	// merge — no HTTP roundtrip.
	it("does NOT invalidate on letter_pending — no letter body change on the backend", () => {
		const { client, updater, invalidations, seed } = makeFakeQueryClient();
		seed(baseDetail);

		applyApplicationEvent(client, eventFor(1, "letter_pending"));

		expect(updater.called).toBe(true);
		expect(updater.result?.status).toBe("letter_pending");
		expect(invalidations).toEqual([]);
	});

	it("does NOT invalidate on letter_sending — worker in flight, no letter change", () => {
		const { client, invalidations, seed } = makeFakeQueryClient();
		seed(baseDetail);

		applyApplicationEvent(client, eventFor(1, "letter_sending"));

		expect(invalidations).toEqual([]);
	});

	it("invalidates on letter_ready — regeneration finished, latest_letter changed", () => {
		const { client, invalidations, seed } = makeFakeQueryClient();
		seed({ ...baseDetail, status: "letter_pending" });

		applyApplicationEvent(client, eventFor(1, "letter_ready"));

		expect(invalidations).toEqual(
			expect.arrayContaining([
				applicationQueryKey(1),
				coverLettersHistoryQueryKey(1),
			]),
		);
	});

	it("invalidates on error — reason field committed to the DB, worth refetching", () => {
		const { client, invalidations, seed } = makeFakeQueryClient();
		seed({ ...baseDetail, status: "letter_sending" });

		applyApplicationEvent(client, eventFor(1, "error", "captcha"));

		expect(invalidations).toEqual(
			expect.arrayContaining([applicationQueryKey(1)]),
		);
	});

	it("preserves retry_count and timestamps not carried in the WS event", () => {
		const { client, updater, seed } = makeFakeQueryClient();
		seed({ ...baseDetail, retry_count: 2 });

		applyApplicationEvent(client, eventFor(1, "error", "network timeout"));

		expect(updater.result?.retry_count).toBe(2);
		expect(updater.result?.created_at).toBe(baseDetail.created_at);
		expect(updater.result?.updated_at).toBe(baseDetail.updated_at);
	});
});
