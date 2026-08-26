import { describe, expect, it, vi } from "vitest";
import { onBackendExit } from "./backend-exit";

describe("onBackendExit", () => {
	it("delegates to the shell bridge and returns its unsubscribe", () => {
		const unsubscribe = vi.fn();
		const bridgeOnExit = vi.fn(() => unsubscribe);
		vi.stubGlobal("otklik", { onBackendExit: bridgeOnExit });

		const handler = vi.fn();
		const off = onBackendExit(handler);

		expect(bridgeOnExit).toHaveBeenCalledWith(handler);
		expect(off).toBe(unsubscribe);
	});
});
