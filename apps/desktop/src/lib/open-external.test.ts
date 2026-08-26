import { beforeEach, describe, expect, it, vi } from "vitest";

const openExternalSpy = vi.fn();
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
		openExternalSpy.mockReset();
		logError.mockReset();
		vi.stubGlobal("otklik", { openExternal: openExternalSpy });
	});

	it("forwards the url to the shell opener", async () => {
		openExternalSpy.mockResolvedValue(undefined);
		await openExternal("https://console.groq.com/keys");
		expect(openExternalSpy).toHaveBeenCalledWith(
			"https://console.groq.com/keys",
		);
	});

	it("swallows opener failures instead of throwing", async () => {
		openExternalSpy.mockRejectedValue(new Error("no opener"));
		await expect(openExternal("https://x")).resolves.toBeUndefined();
		expect(logError).toHaveBeenCalled();
	});
});
