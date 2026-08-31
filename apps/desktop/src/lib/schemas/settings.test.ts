import type { Settings } from "$lib/api/types";
import { describe, expect, it, vi } from "vitest";
import {
	apiDeploymentToForm,
	formDeploymentToAPI,
	makeDeploymentId,
	settingsFormSchema,
	settingsToWrite,
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
			user: { auto_generate: false, auto_submit: false },
			rate_limits: {
				daily_limit: 30,
				hourly_limit: 5,
				min_delay_ms: 800,
				delay_jitter_ms: 400,
			},
			notifications: {
				enabled: true,
				vacancy_parsed: false,
				letter_generated: true,
				letter_generated_sandbox: true,
				application_sent: true,
				error: true,
				captcha: true,
				auth_required: true,
				search_finished: true,
				rate_limited: true,
			},
			llm: {
				resume_text: "",
				letter_style: "",
				system_prompt: "",
				proxy_url: "",
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

describe("formDeploymentToAPI", () => {
	it("untouched key field sends null — «не трогать», не «удалить»", () => {
		const form = {
			id: "a",
			model: "m",
			api_base: "",
			has_api_key: true,
			api_key: "",
			clear_api_key: false,
		};
		expect(formDeploymentToAPI(form).api_key).toBeNull();
	});

	it("typed key is sent as-is", () => {
		const form = {
			id: "a",
			model: "m",
			api_base: "",
			has_api_key: false,
			api_key: "sk-new",
			clear_api_key: false,
		};
		expect(formDeploymentToAPI(form).api_key).toBe("sk-new");
	});

	it("explicit clear sends the empty-string sentinel", () => {
		const form = {
			id: "a",
			model: "m",
			api_base: "",
			has_api_key: true,
			api_key: "",
			clear_api_key: true,
		};
		expect(formDeploymentToAPI(form).api_key).toBe("");
	});

	it("clear wins over a typed buffer", () => {
		const form = {
			id: "a",
			model: "m",
			api_base: "",
			has_api_key: true,
			api_key: "sk-x",
			clear_api_key: true,
		};
		expect(formDeploymentToAPI(form).api_key).toBe("");
	});

	it("round-trips the backend id", () => {
		expect(
			formDeploymentToAPI(
				apiDeploymentToForm({ id: "abc", model: "m", has_api_key: true }),
			).id,
		).toBe("abc");
	});
});

describe("apiDeploymentToForm", () => {
	it("keeps has_api_key for display and leaves the buffer empty", () => {
		const form = apiDeploymentToForm({
			id: "a",
			model: "m",
			api_base: null,
			has_api_key: true,
		});
		expect(form.has_api_key).toBe(true);
		expect(form.api_key).toBe("");
		expect(form.clear_api_key).toBe(false);
	});
});

describe("settingsToWrite", () => {
	const base: Settings = {
		search: { max_pages: 5, max_vacancies: 50 },
		user: { auto_generate: true, auto_submit: false },
		rate_limits: {
			daily_limit: 30,
			hourly_limit: 5,
			min_delay_ms: 800,
			delay_jitter_ms: 400,
		},
		notifications: {
			enabled: true,
			vacancy_parsed: false,
			letter_generated: true,
			letter_generated_sandbox: true,
			application_sent: true,
			error: true,
			captcha: true,
			auth_required: true,
			search_finished: true,
			rate_limited: true,
		},
		llm: {
			resume_text: "r",
			letter_style: "s",
			system_prompt: null,
			proxy_url: null,
			deployments: [
				{ id: "a", model: "gpt", api_base: "https://x", has_api_key: true },
			],
		},
	};

	it("preserves stored deployment keys by sending api_key null", () => {
		const write = settingsToWrite(base);
		expect(write.llm.deployments).toEqual([
			{ id: "a", model: "gpt", api_base: "https://x", api_key: null },
		]);
	});

	it("carries notification flags through unchanged", () => {
		expect(settingsToWrite(base).notifications).toEqual(base.notifications);
	});

	it("carries user flags through unchanged so a queue-page toggle can patch them", () => {
		expect(settingsToWrite(base).user).toEqual({
			auto_generate: true,
			auto_submit: false,
		});
	});
});

describe("makeDeploymentId", () => {
	it("delegates to crypto.randomUUID and strips dashes to match the backend's hex id form", () => {
		const spy = vi
			.spyOn(crypto, "randomUUID")
			.mockReturnValue("00000000-0000-0000-0000-000000000000");
		expect(makeDeploymentId()).toBe("00000000000000000000000000000000");
		expect(spy).toHaveBeenCalledTimes(1);
		spy.mockRestore();
	});

	it("produces distinct ids across invocations (real crypto)", () => {
		const a = makeDeploymentId();
		const b = makeDeploymentId();
		expect(a).not.toBe(b);
	});
});
