import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import type { ApplicationDetail, ApplicationEvent } from "$lib/api/types";
import { applicationQueryKey, applyApplicationEvent } from "./applications";

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
	seed: (data: ApplicationDetail | null) => void;
} {
	let seeded: ApplicationDetail | null = null;
	const updater = {
		called: false,
		key: undefined as unknown,
		result: null as ApplicationDetail | null,
	};
	const client = {
		setQueryData: vi.fn(
			(
				key: unknown,
				fn: (prev: ApplicationDetail | null) => ApplicationDetail | null,
			) => {
				updater.called = true;
				updater.key = key;
				updater.result = fn(seeded);
			},
		),
	} as unknown as QueryClient;
	return {
		client,
		updater,
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
): ApplicationEvent {
	return {
		type: "application_event",
		data: {
			vacancy_id,
			application_id: 100,
			status,
			reason,
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

	it("passes through when the cache is empty (no crash, returns null)", () => {
		const { client, updater, seed } = makeFakeQueryClient();
		seed(null);

		applyApplicationEvent(client, eventFor(1, "letter_ready"));

		expect(updater.result).toBeNull();
	});

	it("routes updates by vacancy_id in the query key", () => {
		const { client, updater } = makeFakeQueryClient();

		applyApplicationEvent(client, eventFor(42, "skipped"));

		expect(updater.key).toEqual(applicationQueryKey(42));
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
