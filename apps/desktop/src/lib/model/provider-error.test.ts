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

	it.each([
		"no deployments configured",
		"Failed to generate cover letter: no deployments configured",
	])(
		"explains %s as an unconfigured model, pointing at Настройки → AI",
		(raw) => {
			expect(explainProviderError(raw)).toContain("Настройки → AI");
		},
	);

	it("explains a real GigaChat missing-credentials blob, pointing at Настройках → AI", () => {
		// Реальный текст, снятый с живого прогона: GigaChat-пресет пишется с
		// пустым ключом, и генерация падает этим многострочным блобом
		// LiteLLM. Ни "401"/"unauthorized" в нём нет, ни "api key" (там
		// подчёркивание — GIGACHAT_API_KEY) — существующие хинты его не ловят.
		const raw =
			"litellm.APIConnectionError: GigachatException - GigaChat credentials not provided. Set GIGACHAT_CREDENTIALS or GIGACHAT_API_KEY environment variable... Received Model Group=gigachat/GigaChat-2 / Available Model Group Fallbacks=[] / Error doing the fallback: ... LiteLLM Retried: 2 times";
		expect(explainProviderError(raw)).toContain("Настройках");
	});

	it("passes an unrecognized message through unchanged — no false confidence", () => {
		expect(explainProviderError("database is locked")).toBe(
			"database is locked",
		);
	});
});
