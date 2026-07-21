import { beforeEach, describe, expect, it, vi } from "vitest";

const check = vi.fn();
vi.mock("@tauri-apps/plugin-updater", () => ({ check: () => check() }));
vi.mock("@tauri-apps/plugin-process", () => ({ relaunch: vi.fn() }));

const invoke = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
	invoke: (cmd: string) => invoke(cmd),
}));

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

describe("updater.install", () => {
	let order: string[];

	function fakeUpdate() {
		return {
			version: "0.2.1",
			download: vi.fn(async () => {
				order.push("download");
			}),
			install: vi.fn(async () => {
				order.push("install");
			}),
			downloadAndInstall: vi.fn(async () => {
				order.push("downloadAndInstall");
			}),
		};
	}

	beforeEach(() => {
		order = [];
		invoke.mockReset();
		invoke.mockImplementation((cmd: string) => {
			order.push(`invoke:${cmd}`);
			return Promise.resolve();
		});
		updater.error = null;
		updater.installing = false;
		updater.available = fakeUpdate() as never;
	});

	it("гасит бэкенд перед установкой — иначе Windows не даст перезаписать его файлы", async () => {
		await updater.install();

		expect(order).toEqual(["download", "invoke:shutdown_backend", "install"]);
	});

	it("не гасит бэкенд, пока обновление не скачано", async () => {
		const update = fakeUpdate();
		update.download = vi.fn(async () => {
			order.push("download");
			throw new Error("network died");
		});
		updater.available = update as never;

		await updater.install();

		expect(order).toEqual(["download"]);
		expect(updater.error).toContain("network died");
	});
});
