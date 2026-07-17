import { beforeEach, describe, expect, it, vi } from "vitest";

const chromium = vi.fn();
const state = vi.fn();
vi.mock("$lib/api/client", () => ({
	API: {
		setup: {
			chromium: () => chromium(),
			state: () => state(),
		},
	},
}));
vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

import { BrowserFlow } from "./browser-flow.svelte";

async function* progressTo(...percents: number[]) {
	for (const percent of percents) {
		yield { status: "downloading", percent, done: false };
	}
	yield { status: "done", percent: 100, done: true };
}

describe("BrowserFlow", () => {
	beforeEach(() => {
		chromium.mockReset();
		state.mockReset();
	});

	it("пропускает загрузку, когда Chromium уже стоит", async () => {
		state.mockResolvedValue({ chromium_installed: true });
		const flow = new BrowserFlow();
		await flow.start();
		expect(flow.screen).toBe("ready");
		expect(chromium).not.toHaveBeenCalled();
	});

	it("качает и доводит прогресс до конца", async () => {
		state.mockResolvedValue({ chromium_installed: false });
		chromium.mockReturnValue(progressTo(10, 50));
		const flow = new BrowserFlow();
		await flow.start();
		expect(flow.percent).toBe(100);
		expect(flow.screen).toBe("ready");
	});

	it("показывает ошибку и разрешает повтор", async () => {
		state.mockResolvedValue({ chromium_installed: false });
		chromium.mockImplementation(() => {
			throw new Error("network is down");
		});
		const flow = new BrowserFlow();
		await flow.start();
		expect(flow.screen).toBe("error");
		expect(flow.error).toContain("network is down");

		chromium.mockReturnValue(progressTo(100));
		await flow.retry();
		expect(flow.screen).toBe("ready");
		expect(flow.error).toBeNull();
	});

	it("не запускает вторую загрузку поверх идущей", async () => {
		state.mockResolvedValue({ chromium_installed: false });
		chromium.mockReturnValue(progressTo(10));
		const flow = new BrowserFlow();
		const first = flow.start();
		await flow.start();
		await first;
		expect(chromium).toHaveBeenCalledTimes(1);
	});
});
