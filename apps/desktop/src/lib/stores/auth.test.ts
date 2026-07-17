import { describe, expect, it, vi } from "vitest";

vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

const { AuthStore } = await import("./auth.svelte");

describe("AuthStore state machine", () => {
	it("starts in status='unknown' and is not authorizing", () => {
		const s = new AuthStore();
		expect(s.state).toEqual({ status: "unknown" });
		expect(s.canAuthorize).toBe(true);
		expect(s.canCancel).toBe(false);
	});

	it("authorizing() from unknown → authorizing", () => {
		const s = new AuthStore();
		s.authorizing();
		expect(s.state.status).toBe("authorizing");
		expect(s.canAuthorize).toBe(false);
		expect(s.canCancel).toBe(true);
	});

	it("authorizing() from unauthorized → authorizing (canAuthorize covers both)", () => {
		const s = new AuthStore();
		s.unauthorized();
		s.authorizing();
		expect(s.state.status).toBe("authorizing");
	});

	it("authorizing() from authorized throws (invalid transition)", () => {
		const s = new AuthStore();
		s.authorized();
		expect(() => s.authorizing()).toThrow(/Cannot be transited to/);
	});

	it("cancel() from authorizing → unknown", () => {
		const s = new AuthStore();
		s.authorizing();
		s.cancel();
		expect(s.state.status).toBe("unknown");
	});

	it("cancel() from unauthorized throws (canCancel is false)", () => {
		const s = new AuthStore();
		s.unauthorized();
		expect(() => s.cancel()).toThrow(/Cannot be transited to/);
	});

	it("authorized() always succeeds without a guard (no throw)", () => {
		const s = new AuthStore();
		s.authorizing();
		s.authorized();
		expect(s.state.status).toBe("authorized");
	});

	it("failed(reason) stores the reason and leaves the failed state", () => {
		const s = new AuthStore();
		s.failed("network down");
		expect(s.state).toEqual({ status: "failed", reason: "network down" });
	});

	it("clear() resets to unknown from any state", () => {
		const s = new AuthStore();
		s.authorized();
		s.clear();
		expect(s.state.status).toBe("unknown");

		s.failed("x");
		s.clear();
		expect(s.state.status).toBe("unknown");
	});

	it("canAuthorize gate: only unknown/unauthorized", () => {
		const s = new AuthStore();
		expect(s.canAuthorize).toBe(true);
		s.unauthorized();
		expect(s.canAuthorize).toBe(true);
		s.authorizing();
		expect(s.canAuthorize).toBe(false);
		s.authorized();
		expect(s.canAuthorize).toBe(false);
		s.clear();
		s.failed("x");
		expect(s.canAuthorize).toBe(false);
	});

	it("canCancel gate: only authorizing", () => {
		const s = new AuthStore();
		expect(s.canCancel).toBe(false);
		s.authorizing();
		expect(s.canCancel).toBe(true);
		s.authorized();
		expect(s.canCancel).toBe(false);
	});
});
