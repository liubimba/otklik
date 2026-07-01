import { getLogger } from "$lib/log";
import { APIError } from "./error";
import type {
	AICoverLetterResponse,
	APIRequestError,
	APIResponse,
	ApplicationDetail,
	AuthStatus,
	CoverLetter,
	FilterSessionConfirm,
	NewFilterSession,
	OrchestratorStatus,
	RateLimitsBudget,
	SearchData,
	Settings,
	Vacancy,
} from "./types";

const BASE_IP = import.meta.env.VITE_BACKEND_IP;
const BASE_PORT = import.meta.env.VITE_BACKEND_PORT;
const logger = getLogger("APIClient");

function formatErrorDetail(detail: APIRequestError["detail"]): string {
	if (typeof detail === "string") return detail;
	if (Array.isArray(detail)) {
		return detail.map((d) => `${d.loc.join(".")}: ${d.msg}`).join("; ");
	}
	return "unknown error";
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
	const url = `http://${BASE_IP}:${BASE_PORT}/api/v1/${path}`;
	logger.info(
		`Making API request to "${url}" with method: ${init?.method || "GET"}. Body: ${init?.body}`,
	);
	const res = await fetch(url, {
		...init,
		headers: {
			"Content-Type": "application/json",
			...init?.headers,
		},
	});
	const data = await res.text();
	logger.info(
		`API request to "${url}" returned status: ${res.status}. Response: ${data}`,
	);
	if (!res.ok) {
		let parsed: APIRequestError = {};
		try {
			parsed = JSON.parse(data) as APIRequestError;
		} catch {
			/* non-JSON body */
		}
		throw new APIError(res.status, formatErrorDetail(parsed.detail));
	}
	return JSON.parse(data) as T;
}

async function api404Null<T>(
	path: string,
	init?: RequestInit,
): Promise<T | null> {
	try {
		return await api<T>(path, init);
	} catch (e) {
		if (e instanceof APIError && e.status === 404) return null;
		throw e;
	}
}

async function apiNullable204<T>(
	path: string,
	init?: RequestInit,
): Promise<T | null> {
	const url = `http://${BASE_IP}:${BASE_PORT}/api/v1/${path}`;
	const res = await fetch(url, {
		...init,
		headers: {
			"Content-Type": "application/json",
			...init?.headers,
		},
	});
	if (res.status === 204) return null;
	const data = await res.text();
	if (!res.ok) {
		let parsed: APIRequestError = {};
		try {
			parsed = JSON.parse(data) as APIRequestError;
		} catch {
			/* non-JSON */
		}
		throw new APIError(res.status, formatErrorDetail(parsed.detail));
	}
	return JSON.parse(data) as T;
}

export const API = {
	auth: {
		status: () => api<AuthStatus>("auth/status"),
		signIn: () => api<AuthStatus>("auth/sign-in", { method: "POST" }),
		signInCancel: () =>
			api<AuthStatus>("auth/sign-in/cancel", { method: "POST" }),
		signOut: () => api<AuthStatus>("auth/sign-out", { method: "POST" }),
	},
	search: {
		filter: {
			open: () =>
				api<NewFilterSession>("search/filter/new", { method: "POST" }),
			confirm: (sessionId: string) =>
				api<FilterSessionConfirm>(`search/filter/${sessionId}/confirm`, {
					method: "POST",
				}),
			cancel: (sessionId: string) =>
				api<APIResponse>(`search/filter/${sessionId}/cancel`, {
					method: "POST",
				}),
		},
		parse: {
			start: (
				url: string,
				max_pages?: number | null,
				max_vacancies?: number | null,
			) =>
				api<SearchData>("search/parse/start", {
					method: "POST",
					body: JSON.stringify({ url, max_pages, max_vacancies }),
				}),
			current: () => apiNullable204<SearchData>("search/parse/current"),
			cancel: (searchId: string) =>
				api<APIResponse>(`search/parse/${searchId}`, { method: "DELETE" }),
		},
	},
	vacancies: {
		list: () => api<Vacancy[]>("vacancies/"),
		get: (vacancyId: number) => api<Vacancy>(`vacancies/${vacancyId}`),
	},
	application: {
		get: (vacancyId: number) =>
			api404Null<ApplicationDetail>(`vacancies/${vacancyId}/application`),
		letters: (vacancyId: number) =>
			api<CoverLetter[]>(`vacancies/${vacancyId}/application/letters`),
		generate: (vacancyId: number) =>
			api<AICoverLetterResponse>(
				`vacancies/${vacancyId}/application/generate`,
				{ method: "POST" },
			),
		save: (vacancyId: number, text: string) =>
			api<CoverLetter>(`vacancies/${vacancyId}/application/save`, {
				method: "POST",
				body: JSON.stringify({ text }),
			}),
		submit: (vacancyId: number, text?: string) =>
			api<ApplicationDetail>(`vacancies/${vacancyId}/application/submit`, {
				method: "POST",
				body: JSON.stringify(text !== undefined ? { text } : {}),
			}),
		skip: (vacancyId: number) =>
			api<ApplicationDetail>(`vacancies/${vacancyId}/application/skip`, {
				method: "POST",
			}),
		retry: (vacancyId: number) =>
			api<ApplicationDetail>(`vacancies/${vacancyId}/application/retry`, {
				method: "POST",
			}),
	},
	settings: {
		get: () => api<Settings>("settings"),
		update: (body: Settings) =>
			api<Settings>("settings", {
				method: "PUT",
				body: JSON.stringify(body),
			}),
	},
	system: {
		rateLimits: () => api<RateLimitsBudget>("system/rate-limits"),
		aiHealth: () => api<{ status: string }>("system/ai/health"),
		orchestrator: {
			status: () =>
				api<OrchestratorStatus>("system/orchestrator/status"),
			resume: () =>
				api<APIResponse>("system/orchestrator/resume", { method: "POST" }),
		},
	},
} as const;
