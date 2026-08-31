import type {
	LLMDeployment,
	LLMDeploymentWrite,
	Settings,
	SettingsWrite,
} from "$lib/api/types";
import { z } from "zod";

const positiveInt = z.coerce.number().int().positive();
const nonNegativeInt = z.coerce.number().int().nonnegative();

const llmDeploymentSchema = z.object({
	id: z.string(),
	model: z.string().min(1, "Укажите модель"),
	api_base: z.string().default(""),
	has_api_key: z.boolean().default(false),
	api_key: z.string().default(""),
	clear_api_key: z.boolean().default(false),
});

export const settingsFormSchema = z.object({
	search: z.object({
		max_pages: positiveInt.default(5),
		max_vacancies: positiveInt.default(50),
	}),
	user: z.object({
		auto_generate: z.boolean().default(false),
		auto_submit: z.boolean().default(false),
	}),
	rate_limits: z.object({
		daily_limit: positiveInt.default(30),
		hourly_limit: positiveInt.default(5),
		min_delay_ms: nonNegativeInt.default(800),
		delay_jitter_ms: nonNegativeInt.default(400),
	}),
	notifications: z
		.object({
			enabled: z.boolean().default(true),
			vacancy_parsed: z.boolean().default(false),
			letter_generated: z.boolean().default(true),
			letter_generated_sandbox: z.boolean().default(true),
			application_sent: z.boolean().default(true),
			error: z.boolean().default(true),
			captcha: z.boolean().default(true),
			auth_required: z.boolean().default(true),
			search_finished: z.boolean().default(true),
			rate_limited: z.boolean().default(true),
		})
		.default(() => ({
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
		})),
	llm: z.object({
		resume_text: z.string().default(""),
		letter_style: z.string().default(""),
		system_prompt: z.string().default(""),
		proxy_url: z.string().default(""),
		deployments: z.array(llmDeploymentSchema).default([]),
	}),
});

export type LLMDeploymentForm = z.infer<typeof llmDeploymentSchema>;
export type SettingsFormData = z.infer<typeof settingsFormSchema>;

export function makeDeploymentId(): string {
	return crypto.randomUUID().replace(/-/g, "");
}

export function apiDeploymentToForm(d: LLMDeployment): LLMDeploymentForm {
	return {
		id: d.id,
		model: d.model,
		api_base: d.api_base ?? "",
		has_api_key: d.has_api_key,
		api_key: "",
		clear_api_key: false,
	};
}

export function formDeploymentToAPI(d: LLMDeploymentForm): LLMDeploymentWrite {
	return {
		id: d.id,
		model: d.model,
		api_base: d.api_base.trim() ? d.api_base : null,
		api_key: d.clear_api_key ? "" : d.api_key.trim() ? d.api_key : null,
	};
}

export function settingsToWrite(settings: Settings): SettingsWrite {
	return {
		search: settings.search,
		user: settings.user,
		rate_limits: settings.rate_limits,
		notifications: settings.notifications,
		llm: {
			resume_text: settings.llm.resume_text,
			letter_style: settings.llm.letter_style,
			system_prompt: settings.llm.system_prompt ?? null,
			proxy_url: settings.llm.proxy_url ?? null,
			deployments: settings.llm.deployments.map((d) => ({
				id: d.id,
				model: d.model,
				api_base: d.api_base ?? null,
				api_key: null,
			})),
		},
	};
}
