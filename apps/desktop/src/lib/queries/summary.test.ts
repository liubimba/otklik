import {
	invalidateSummary,
	summaryQueryKey,
	summaryScopeQueryKey,
} from "$lib/queries/summary";
import { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";

// The endpoint path itself is pinned in api/client.test.ts, next to every other
// URL assertion. What is worth testing here is the invalidation: the WS handler
// fires it on every application-status change, and a wrong key would leave the
// counter stale forever — silently, since nothing else reads this cache entry.
describe("summary query", () => {
	// The two sidebar rows count different things, so they must not share a cache
	// entry — «Очередь» is scoped to the latest search, «Все вакансии» is global.
	it("gives each scope its own cache key", () => {
		expect(summaryScopeQueryKey("all")).not.toEqual(
			summaryScopeQueryKey("latest"),
		);
		// ...but both sit under the prefix, so one invalidation sweeps both.
		expect(summaryScopeQueryKey("all").slice(0, 1)).toEqual([
			...summaryQueryKey,
		]);
		expect(summaryScopeQueryKey("latest").slice(0, 1)).toEqual([
			...summaryQueryKey,
		]);
	});

	it("invalidates the prefix, refreshing every scope at once", () => {
		const queryClient = new QueryClient();
		const spy = vi.spyOn(queryClient, "invalidateQueries");

		invalidateSummary(queryClient);

		expect(spy).toHaveBeenCalledWith({ queryKey: summaryQueryKey });
	});
});
