import { describe, expect, it } from "vitest";
import { explainProviderError } from "./provider-error";

/**
 * Pure-function coverage of the three provider-error categories from
 * Task 12, plus the "show it as-is" fallback. Real paraglide messages
 * (not mocked) — this is what letter-review-sheet.viewmodel.test.ts and
 * the toasts in letter-review-sheet.view.svelte.ts actually render.
 */
describe("explainProviderError", () => {
	it.each([
		"connection refused",
		"ECONNREFUSED",
		"Failed to connect to localhost:11434",
	])("explains %s as an unreachable model, pointing at Ollama", (raw) => {
		expect(explainProviderError(raw)).toContain("Ollama");
	});

	it.each(["401 invalid api key", "403 forbidden", "Unauthorized"])(
		"explains %s as a rejected key, pointing at Настройки → AI",
		(raw) => {
			expect(explainProviderError(raw)).toContain("Настройках");
		},
	);

	it.each(["Request timeout", "operation timed out"])(
		"explains %s as a slow model, suggesting a cloud key",
		(raw) => {
			expect(explainProviderError(raw)).toContain("облачный ключ");
		},
	);

	it("passes an unrecognized message through unchanged — no false confidence", () => {
		expect(explainProviderError("database is locked")).toBe(
			"database is locked",
		);
	});
});
