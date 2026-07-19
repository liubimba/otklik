import { beforeEach, describe, expect, it, vi } from "vitest";

const openUrl = vi.fn();
vi.mock("@tauri-apps/plugin-opener", () => ({
	openUrl: (url: string) => openUrl(url),
}));
const logError = vi.fn();
vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: (msg: string) => logError(msg),
	}),
}));

import { openExternal } from "./open-external";

describe("openExternal", () => {
	beforeEach(() => {
		openUrl.mockReset();
		logError.mockReset();
	});

	it("forwards the url to the Tauri opener", async () => {
		openUrl.mockResolvedValue(undefined);
		await openExternal("https://console.groq.com/keys");
		expect(openUrl).toHaveBeenCalledWith("https://console.groq.com/keys");
	});

	it("swallows opener failures instead of throwing", async () => {
		openUrl.mockRejectedValue(new Error("no opener"));
		await expect(openExternal("https://x")).resolves.toBeUndefined();
		expect(logError).toHaveBeenCalled();
	});
});
