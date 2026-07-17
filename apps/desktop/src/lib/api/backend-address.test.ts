import { beforeEach, describe, expect, it, vi } from "vitest";

const invoke = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
	invoke: (cmd: string) => invoke(cmd),
}));

import { backendOrigin, resetBackendAddress } from "./backend-address";

describe("backendOrigin", () => {
	beforeEach(() => {
		invoke.mockReset();
		resetBackendAddress();
	});

	it("собирает адрес из порта, который выдал Tauri", async () => {
		invoke.mockResolvedValue(45678);
		expect(await backendOrigin()).toBe("127.0.0.1:45678");
	});

	it("спрашивает порт один раз и кэширует", async () => {
		invoke.mockResolvedValue(45678);
		await backendOrigin();
		await backendOrigin();
		expect(invoke).toHaveBeenCalledTimes(1);
	});

	it("не кэширует неудачу — следующий вызов спросит снова", async () => {
		invoke.mockRejectedValueOnce(new Error("no backend"));
		await expect(backendOrigin()).rejects.toThrow();
		invoke.mockResolvedValue(45678);
		expect(await backendOrigin()).toBe("127.0.0.1:45678");
	});
});
