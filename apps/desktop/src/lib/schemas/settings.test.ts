import { describe, expect, it, vi } from "vitest";
import {
	apiDeploymentToForm,
	formDeploymentToAPI,
	makeDeploymentId,
	settingsFormSchema,
} from "./settings";

describe("settingsFormSchema — defaults", () => {
	it("fills every optional field with sane defaults from empty input", () => {
		const parsed = settingsFormSchema.parse({
			search: {},
			user: {},
			rate_limits: {},
			llm: {},
		});

		expect(parsed).toEqual({
			search: { max_pages: 5, max_vacancies: 50 },
			user: { auto_submit: false },
			rate_limits: {
				daily_limit: 30,
				hourly_limit: 5,
				min_delay_ms: 800,
				delay_jitter_ms: 400,
			},
			llm: {
				resume_text: "",
				letter_style: "",
				system_prompt: "",
				deployments: [],
			},
		});
	});
});

describe("settingsFormSchema — coercion + validation", () => {
	it("coerces string numeric inputs into positive integers", () => {
		const parsed = settingsFormSchema.parse({
			search: { max_pages: "7", max_vacancies: "100" },
			user: {},
			rate_limits: { daily_limit: "40", hourly_limit: "6" },
			llm: {},
		});
		expect(parsed.search.max_pages).toBe(7);
		expect(parsed.search.max_vacancies).toBe(100);
		expect(parsed.rate_limits.daily_limit).toBe(40);
	});

	it("rejects zero / negative for `positive` fields", () => {
		const bad = settingsFormSchema.safeParse({
			search: { max_pages: 0, max_vacancies: 50 },
			user: {},
			rate_limits: {},
			llm: {},
		});
		expect(bad.success).toBe(false);
	});

	it("accepts zero for `nonnegative` delay fields", () => {
		const parsed = settingsFormSchema.parse({
			search: {},
			user: {},
			rate_limits: { min_delay_ms: 0, delay_jitter_ms: 0 },
			llm: {},
		});
		expect(parsed.rate_limits.min_delay_ms).toBe(0);
		expect(parsed.rate_limits.delay_jitter_ms).toBe(0);
	});

	it("rejects a deployment with empty model string", () => {
		const bad = settingsFormSchema.safeParse({
			search: {},
			user: {},
			rate_limits: {},
			llm: {
				deployments: [{ id: "x", model: "", api_key: "k", api_base: "" }],
			},
		});
		expect(bad.success).toBe(false);
	});
});

describe("apiDeploymentToForm / formDeploymentToAPI round-trip", () => {
	it("apiDeploymentToForm assigns a fresh id and normalises nulls to empty strings", () => {
		const form = apiDeploymentToForm({
			model: "openai/gpt-4o",
			api_key: null,
			api_base: null,
		});
		expect(form.model).toBe("openai/gpt-4o");
		expect(form.api_key).toBe("");
		expect(form.api_base).toBe("");
		expect(form.id).toEqual(expect.any(String));
		expect(form.id.length).toBeGreaterThan(0);
	});

	it("formDeploymentToAPI reverses empty strings back to null", () => {
		const api = formDeploymentToAPI({
			id: "any",
			model: "groq/llama",
			api_key: "   ",
			api_base: "",
		});
		expect(api).toEqual({
			model: "groq/llama",
			api_key: null,
			api_base: null,
		});
	});

	it("formDeploymentToAPI preserves non-empty values verbatim", () => {
		const api = formDeploymentToAPI({
			id: "any",
			model: "groq/llama",
			api_key: "sk-live-xyz",
			api_base: "https://api.example",
		});
		expect(api).toEqual({
			model: "groq/llama",
			api_key: "sk-live-xyz",
			api_base: "https://api.example",
		});
	});

	it("api → form → api leaves the payload semantically identical", () => {
		const original = {
			model: "openai/gpt-4o",
			api_key: "sk-a",
			api_base: null,
		};
		const roundtrip = formDeploymentToAPI(apiDeploymentToForm(original));
		expect(roundtrip).toEqual(original);
	});
});

describe("makeDeploymentId", () => {
	it("delegates to crypto.randomUUID", () => {
		const spy = vi
			.spyOn(crypto, "randomUUID")
			.mockReturnValue("00000000-0000-0000-0000-000000000000");
		expect(makeDeploymentId()).toBe("00000000-0000-0000-0000-000000000000");
		expect(spy).toHaveBeenCalledTimes(1);
		spy.mockRestore();
	});

	it("produces distinct ids across invocations (real crypto)", () => {
		const a = makeDeploymentId();
		const b = makeDeploymentId();
		expect(a).not.toBe(b);
	});
});
