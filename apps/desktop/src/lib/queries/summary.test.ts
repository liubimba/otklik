import { invalidateSummary, summaryQueryKey } from "$lib/queries/summary";
import { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";

// The endpoint path itself is pinned in api/client.test.ts, next to every other
// URL assertion. What is worth testing here is the invalidation: the WS handler
// fires it on every application-status change, and a wrong key would leave the
// counter stale forever — silently, since nothing else reads this cache entry.
describe("summary query", () => {
	it("invalidates exactly its own key", () => {
		const queryClient = new QueryClient();
		const spy = vi.spyOn(queryClient, "invalidateQueries");

		invalidateSummary(queryClient);

		expect(spy).toHaveBeenCalledWith({ queryKey: summaryQueryKey });
	});
});
