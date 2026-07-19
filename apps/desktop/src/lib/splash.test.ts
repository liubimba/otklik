import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { hideAppSplash } from "./splash";

describe("hideAppSplash", () => {
	beforeEach(() => {
		vi.useFakeTimers();
		document.body.innerHTML =
			'<div id="app-splash"><div class="spinner"></div></div>';
	});

	afterEach(() => {
		vi.useRealTimers();
		document.body.innerHTML = "";
	});

	it("fades the splash out, then removes it from the DOM", () => {
		hideAppSplash();

		expect(
			document.getElementById("app-splash")?.classList.contains("is-hidden"),
		).toBe(true);

		vi.runAllTimers();

		expect(document.getElementById("app-splash")).toBeNull();
	});

	it("is a no-op when the splash is already gone", () => {
		document.body.innerHTML = "";
		expect(() => hideAppSplash()).not.toThrow();
	});
});
