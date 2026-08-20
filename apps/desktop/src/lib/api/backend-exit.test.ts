import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));

const { listen } = await import("@tauri-apps/api/event");
const { onBackendExit, BACKEND_EXIT_EVENT } = await import("./backend-exit");

beforeEach(() => {
	vi.mocked(listen).mockReset();
});

describe("onBackendExit", () => {
	it("subscribes to the backend-exit event and forwards the captured stderr", async () => {
		const unlisten = vi.fn();
		let captured: ((e: { payload: unknown }) => void) | undefined;
		vi.mocked(listen).mockImplementation((_name, cb) => {
			captured = cb as typeof captured;
			return Promise.resolve(unlisten);
		});

		const handler = vi.fn();
		const off = await onBackendExit(handler);

		expect(listen).toHaveBeenCalledWith(
			BACKEND_EXIT_EVENT,
			expect.any(Function),
		);
		captured?.({
			payload: { code: 3, stderr: "Can't locate revision '0bdef780d589'" },
		});
		expect(handler).toHaveBeenCalledWith(
			"Can't locate revision '0bdef780d589'",
		);
		expect(off).toBe(unlisten);
	});

	it("forwards undefined when the exit carries no stderr", async () => {
		let captured: ((e: { payload: unknown }) => void) | undefined;
		vi.mocked(listen).mockImplementation((_name, cb) => {
			captured = cb as typeof captured;
			return Promise.resolve(vi.fn());
		});

		const handler = vi.fn();
		await onBackendExit(handler);
		captured?.({ payload: { code: 1, stderr: "" } });
		expect(handler).toHaveBeenCalledWith(undefined);
	});
});
