import { describe, expect, it, vi } from "vitest";
import {
	authCellStatus,
	badgeCount,
	guardedAuthAction,
} from "./app-sidebar.logic";

describe("authCellStatus", () => {
	it("offline wins over any data — profile says 'нет связи', never a stale 'Подключён' or a stuck skeleton (bugs #1/#2)", () => {
		expect(authCellStatus(true, { status: "authorized" })).toBe("offline");
		expect(authCellStatus(true, undefined)).toBe("offline");
	});

	it("online + no data yet → brief loading skeleton (first load only)", () => {
		expect(authCellStatus(false, undefined)).toBe("loading");
	});

	it("online maps the backend status through ('unknown' reads as unauthorized)", () => {
		expect(authCellStatus(false, { status: "authorized" })).toBe("authorized");
		expect(authCellStatus(false, { status: "authorizing" })).toBe(
			"authorizing",
		);
		expect(authCellStatus(false, { status: "unauthorized" })).toBe(
			"unauthorized",
		);
		expect(authCellStatus(false, { status: "unknown" })).toBe("unauthorized");
	});
});

describe("badgeCount", () => {
	it("hides the badge while offline — a frozen count must not look like live vacancies (bug #2)", () => {
		expect(badgeCount(true, 7)).toBeNull();
		expect(badgeCount(true, 0)).toBeNull();
	});

	it("passes the count through while online", () => {
		expect(badgeCount(false, 7)).toBe(7);
		expect(badgeCount(false, 0)).toBe(0);
		expect(badgeCount(false, null)).toBeNull();
	});
});

describe("guardedAuthAction", () => {
	it("surfaces a failing auth action instead of failing silently (bug #2 — 'ничего не происходит')", async () => {
		const onError = vi.fn();
		await guardedAuthAction(
			() => Promise.reject(new Error("Failed to fetch")),
			onError,
		);
		expect(onError).toHaveBeenCalledWith("Failed to fetch");
	});

	it("does not call onError when the action succeeds", async () => {
		const onError = vi.fn();
		await guardedAuthAction(() => Promise.resolve("ok"), onError);
		expect(onError).not.toHaveBeenCalled();
	});
});
