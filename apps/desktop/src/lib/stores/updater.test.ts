import { beforeEach, describe, expect, it, vi } from "vitest";
import { updater } from "./updater.svelte";

const check = vi.fn();
const install = vi.fn();

beforeEach(() => {
	check.mockReset();
	install.mockReset();
	updater.available = null;
	updater.error = null;
	updater.checking = false;
	updater.installing = false;
	vi.stubGlobal("otklik", { updater: { check, install }, log: () => {} });
});

describe("updater.check", () => {
	it("находит обновление", async () => {
		check.mockResolvedValue({ version: "0.3.0" });
		expect(await updater.check()).toBe(true);
		expect(updater.available?.version).toBe("0.3.0");
		expect(updater.error).toBeNull();
	});

	it("нет обновлений — не ошибка", async () => {
		check.mockResolvedValue(null);
		expect(await updater.check()).toBe(false);
		expect(updater.available).toBeNull();
		expect(updater.error).toBeNull();
	});

	it("настоящий сбой показывается пользователю", async () => {
		check.mockRejectedValue(new Error("signature verification failed"));
		expect(await updater.check()).toBe(false);
		expect(updater.error).toContain("signature verification failed");
	});
});

describe("updater.install", () => {
	beforeEach(() => {
		updater.available = { version: "0.2.1" };
	});

	it("делегирует установку мосту", async () => {
		install.mockResolvedValue(undefined);
		await updater.install();
		expect(install).toHaveBeenCalledOnce();
	});

	it("показывает ошибку установки и снимает флаг installing", async () => {
		install.mockRejectedValue(new Error("network died"));
		await updater.install();
		expect(updater.error).toContain("network died");
		expect(updater.installing).toBe(false);
	});
});
