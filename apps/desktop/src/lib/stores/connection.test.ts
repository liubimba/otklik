import { describe, expect, it } from "vitest";
import { ConnectionStore } from "./connection.svelte";

describe("ConnectionStore", () => {
	it("starts in 'connecting' so the offline banner stays quiet on a normal launch", () => {
		const c = new ConnectionStore();
		expect(c.state).toBe("connecting");
		expect(c.isOnline).toBe(false);
		expect(c.isOffline).toBe(false);
	});

	it("online() marks it reachable", () => {
		const c = new ConnectionStore();
		c.online();
		expect(c.state).toBe("online");
		expect(c.isOnline).toBe(true);
		expect(c.isOffline).toBe(false);
	});

	it("offline() marks it unreachable (drives the banner + profile 'нет связи')", () => {
		const c = new ConnectionStore();
		c.offline();
		expect(c.state).toBe("offline");
		expect(c.isOffline).toBe(true);
		expect(c.isOnline).toBe(false);
	});
});
