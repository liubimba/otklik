import type { LLMDeployment } from "$lib/api/types";
import { z } from "zod";

const positiveInt = z.coerce.number().int().positive();
const nonNegativeInt = z.coerce.number().int().nonnegative();

const llmDeploymentSchema = z.object({
	id: z.string(),
	model: z.string().min(1, "Укажите модель"),
	api_key: z.string().default(""),
	api_base: z.string().default(""),
});

export const settingsFormSchema = z.object({
	search: z.object({
		max_pages: positiveInt.default(5),
		max_vacancies: positiveInt.default(50),
	}),
	user: z.object({
		auto_submit: z.boolean().default(false),
	}),
	rate_limits: z.object({
		daily_limit: positiveInt.default(30),
		hourly_limit: positiveInt.default(5),
		min_delay_ms: nonNegativeInt.default(800),
		delay_jitter_ms: nonNegativeInt.default(400),
	}),
	llm: z.object({
		resume_text: z.string().default(""),
		letter_style: z.string().default(""),
		system_prompt: z.string().default(""),
		deployments: z.array(llmDeploymentSchema).default([]),
	}),
});

export type LLMDeploymentForm = z.infer<typeof llmDeploymentSchema>;
export type SettingsFormData = z.infer<typeof settingsFormSchema>;

export function makeDeploymentId(): string {
	return crypto.randomUUID();
}

export function apiDeploymentToForm(d: LLMDeployment): LLMDeploymentForm {
	return {
		id: makeDeploymentId(),
		model: d.model,
		api_key: d.api_key ?? "",
		api_base: d.api_base ?? "",
	};
}

export function formDeploymentToAPI(d: LLMDeploymentForm): LLMDeployment {
	return {
		model: d.model,
		api_key: d.api_key.trim() ? d.api_key : null,
		api_base: d.api_base.trim() ? d.api_base : null,
	};
}
