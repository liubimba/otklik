import type { LLMSettings } from "$lib/api/types";
import { z } from "zod";
const positiveInt = z.coerce.number().int().positive();
const nonNegativeInt = z.coerce.number().int().nonnegative();

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
});

export const defaultLlm: LLMSettings = {
	resume_text: "",
	letter_style: "",
	deployments: [],
};

export type SettingsFormData = z.infer<typeof settingsFormSchema>;
