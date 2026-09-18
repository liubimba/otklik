import type { AuthEvent } from "$lib/api/types";
import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import { applyAuthEvent, authQueryKey } from "./auth";

function makeFakeQueryClient() {
	const invalidateQueries = vi.fn();
	return {
		client: { invalidateQueries } as unknown as QueryClient,
		invalidateQueries,
	};
}

describe("applyAuthEvent", () => {
	it("invalidates the board-agnostic auth key so the active board refetches", () => {
		const { client, invalidateQueries } = makeFakeQueryClient();
		const event: AuthEvent = {
			type: "auth_changed",
			data: { status: "authorized" },
		};

		applyAuthEvent(client, event);

		expect(invalidateQueries).toHaveBeenCalledTimes(1);
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: authQueryKey });
	});

	it.each(["authorized", "unauthorized", "authorizing"] as const)(
		"invalidates regardless of the event status=%s",
		(status) => {
			const { client, invalidateQueries } = makeFakeQueryClient();

			applyAuthEvent(client, { type: "auth_changed", data: { status } });

			expect(invalidateQueries).toHaveBeenCalledWith({
				queryKey: authQueryKey,
			});
		},
	);
});
