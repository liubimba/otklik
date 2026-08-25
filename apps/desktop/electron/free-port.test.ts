import { describe, expect, it } from "vitest";
import { freePort } from "./free-port";

describe("freePort", () => {
	it("returns a usable port number in range", async () => {
		const p = await freePort();
		expect(p).toBeGreaterThan(0);
		expect(p).toBeLessThan(65536);
	});

	it("returns different ports across concurrent calls", async () => {
		const [a, b] = await Promise.all([freePort(), freePort()]);
		expect(a).not.toBe(b);
	});
});
