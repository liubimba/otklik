import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";
import type { AuthEvent } from "$lib/api/types";
import { applyAuthEvent, authQueryKey } from "./auth";

function makeFakeQueryClient() {
	const setQueryData = vi.fn();
	return {
		client: { setQueryData } as unknown as QueryClient,
		setQueryData,
	};
}

describe("applyAuthEvent", () => {
	it("writes the event payload into the auth cache verbatim", () => {
		const { client, setQueryData } = makeFakeQueryClient();
		const event: AuthEvent = {
			type: "auth_changed",
			data: { status: "authorized" },
		};

		applyAuthEvent(client, event);

		expect(setQueryData).toHaveBeenCalledTimes(1);
		expect(setQueryData).toHaveBeenCalledWith(authQueryKey, event.data);
	});

	it("uses the same key for every write (query cache stability)", () => {
		const { client, setQueryData } = makeFakeQueryClient();

		applyAuthEvent(client, {
			type: "auth_changed",
			data: { status: "authorizing" },
		});
		applyAuthEvent(client, {
			type: "auth_changed",
			data: { status: "unauthorized" },
		});

		const [firstKey] = setQueryData.mock.calls[0];
		const [secondKey] = setQueryData.mock.calls[1];
		expect(firstKey).toBe(secondKey);
	});

	it.each(["authorized", "unauthorized", "authorizing"] as const)(
		"forwards status=%s unchanged",
		(status) => {
			const { client, setQueryData } = makeFakeQueryClient();

			applyAuthEvent(client, {
				type: "auth_changed",
				data: { status },
			});

			expect(setQueryData).toHaveBeenCalledWith(authQueryKey, { status });
		},
	);
});
