import { beforeEach, describe, expect, it, vi } from "vitest";
import { backendOrigin, resetBackendAddress } from "./backend-address";

const getBackendPort = vi.fn();

const ok = () => new Response("{}", { status: 200 });

describe("backendOrigin", () => {
	beforeEach(() => {
		getBackendPort.mockReset();
		resetBackendAddress();
		vi.restoreAllMocks();
		getBackendPort.mockResolvedValue(45678);
		vi.stubGlobal("otklik", { getBackendPort });
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok()));
	});

	it("собирает адрес из порта, который выдал шелл", async () => {
		expect(await backendOrigin()).toBe("127.0.0.1:45678");
	});

	it("спрашивает порт один раз и кэширует", async () => {
		await backendOrigin();
		await backendOrigin();
		expect(getBackendPort).toHaveBeenCalledTimes(1);
	});

	it("не кэширует неудачу — следующий вызов спросит снова", async () => {
		getBackendPort.mockRejectedValueOnce(new Error("no backend"));
		await expect(backendOrigin()).rejects.toThrow();
		getBackendPort.mockResolvedValue(45678);
		expect(await backendOrigin()).toBe("127.0.0.1:45678");
	});

	it("ждёт, пока sidecar поднимется, а не бьёт в мёртвый порт", async () => {
		const fetchMock = vi
			.fn()
			.mockRejectedValueOnce(new Error("connection refused"))
			.mockRejectedValueOnce(new Error("connection refused"))
			.mockResolvedValue(ok());
		vi.stubGlobal("fetch", fetchMock);

		expect(await backendOrigin()).toBe("127.0.0.1:45678");
		expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(3);
		expect(fetchMock.mock.calls[0][0]).toBe(
			"http://127.0.0.1:45678/api/v1/system/health",
		);
	});

	it("ждёт только один раз — второй вызов не опрашивает health снова", async () => {
		const fetchMock = vi.fn().mockResolvedValue(ok());
		vi.stubGlobal("fetch", fetchMock);

		await backendOrigin();
		await backendOrigin();
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});
});
