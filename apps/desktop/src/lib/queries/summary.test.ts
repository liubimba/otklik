import {
	invalidateSummary,
	summaryQueryKey,
	summaryScopeQueryKey,
} from "$lib/queries/summary";
import { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it, vi } from "vitest";

describe("summary query", () => {
	it("gives each scope its own cache key", () => {
		expect(summaryScopeQueryKey("all")).not.toEqual(
			summaryScopeQueryKey("latest"),
		);
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
