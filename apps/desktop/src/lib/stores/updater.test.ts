import { beforeEach, describe, expect, it, vi } from "vitest";

const check = vi.fn();
vi.mock("@tauri-apps/plugin-updater", () => ({ check: () => check() }));
vi.mock("@tauri-apps/plugin-process", () => ({ relaunch: vi.fn() }));

import { updater } from "./updater.svelte";

describe("updater.check", () => {
	beforeEach(() => {
		check.mockReset();
		updater.available = null;
		updater.error = null;
	});

	it("находит обновление", async () => {
		check.mockResolvedValue({ version: "0.3.0" });
		expect(await updater.check()).toBe(true);
		expect(updater.error).toBeNull();
	});

	it("нет обновлений — не ошибка", async () => {
		check.mockResolvedValue(null);
		expect(await updater.check()).toBe(false);
		expect(updater.error).toBeNull();
	});

	it("пустой фид — это «нет обновлений», а не ошибка в лицо пользователю", async () => {
		check.mockRejectedValue(
			new Error("Could not fetch a valid release JSON from the remote"),
		);
		expect(await updater.check()).toBe(false);
		expect(updater.error).toBeNull();
	});

	it("недоступный эндпоинт — тоже пустой фид, а не поломка", async () => {
		check.mockRejectedValue(
			new Error(
				"update endpoint did not respond with a successful status code",
			),
		);
		expect(await updater.check()).toBe(false);
		expect(updater.error).toBeNull();
	});

	it("настоящий сбой всё ещё показывается", async () => {
		check.mockRejectedValue(new Error("signature verification failed"));
		expect(await updater.check()).toBe(false);
		expect(updater.error).toContain("signature verification failed");
	});
});
