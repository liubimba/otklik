import type { ApplicationDetail, ApplicationEvent } from "$lib/api/types";
import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import {
	applicationQueryKey,
	applyApplicationEvent,
	coverLettersHistoryQueryKey,
} from "./applications";

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
		expect(updater.result?.latest_letter).toEqual(baseDetail.latest_letter);
		expect(updater.result?.letters_count).toBe(3);
	});

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
		seed({ ...baseDetail, vacancy_id: 42 });

		applyApplicationEvent(client, eventFor(42, "skipped"));

		expect(updater.key).toEqual(applicationQueryKey(42));
	});

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
