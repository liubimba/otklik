import { describe, expect, it } from "vitest";
import { resolveUpdaterProxy } from "./proxy";

describe("resolveUpdaterProxy", () => {
	it("returns null when no proxy env is set", () => {
		expect(resolveUpdaterProxy({})).toBeNull();
	});

	it("reads ALL_PROXY", () => {
		expect(resolveUpdaterProxy({ ALL_PROXY: "socks5://127.0.0.1:10808" })).toBe(
			"socks5://127.0.0.1:10808",
		);
	});

	it("prefers ALL_PROXY over HTTPS_PROXY", () => {
		expect(
			resolveUpdaterProxy({
				ALL_PROXY: "socks5://127.0.0.1:10808",
				HTTPS_PROXY: "http://proxy:3128",
			}),
		).toBe("socks5://127.0.0.1:10808");
	});

	it("falls back to HTTPS_PROXY then HTTP_PROXY", () => {
		expect(resolveUpdaterProxy({ HTTPS_PROXY: "http://a:1" })).toBe(
			"http://a:1",
		);
		expect(resolveUpdaterProxy({ HTTP_PROXY: "http://b:2" })).toBe(
			"http://b:2",
		);
	});

	it("normalizes socks5h to socks5 (Chromium proxyRules has no socks5h)", () => {
		expect(
			resolveUpdaterProxy({ ALL_PROXY: "socks5h://127.0.0.1:10808" }),
		).toBe("socks5://127.0.0.1:10808");
	});

	it("trims whitespace and treats blank as unset", () => {
		expect(resolveUpdaterProxy({ ALL_PROXY: "  socks5://h:1  " })).toBe(
			"socks5://h:1",
		);
		expect(resolveUpdaterProxy({ ALL_PROXY: "   " })).toBeNull();
	});
});
