import type { LLMDeployment, LLMDeploymentWrite } from "$lib/api/types";
import { z } from "zod";

const positiveInt = z.coerce.number().int().positive();
const nonNegativeInt = z.coerce.number().int().nonnegative();

const llmDeploymentSchema = z.object({
	// id теперь приходит с бэкенда и устойчив: он же имя аккаунта в хранилище.
	id: z.string(),
	model: z.string().min(1, "Укажите модель"),
	api_base: z.string().default(""),
	// Из GET — только для отображения «Ключ сохранён».
	has_api_key: z.boolean().default(false),
	// Буфер ввода нового ключа. Пустой — значит «не трогали», а НЕ «удалить».
	api_key: z.string().default(""),
	// Удаление ключа — только явным действием (кнопка в Task 7).
	clear_api_key: z.boolean().default(false),
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

// Локально добавленным строкам нужен ключ для {#each} до того, как бэкенд их
// увидел. Эмитим ту же hex-форму, что и бэкенд — без дефисов.
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
		// Пустое поле — «пользователь его не трогал» (null = не трогать ключ),
		// а НЕ «удалить». Иначе сохранение любой чужой настройки стирало бы все
		// ключи. Удаление — только явным clear_api_key.
		api_key: d.clear_api_key ? "" : d.api_key.trim() ? d.api_key : null,
	};
}
