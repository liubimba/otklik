import { getLogger } from "$lib/log";
import { APIError } from "./error";
import type {
	APIRequestError,
	APIResponse,
	ApplicationDetail,
	ApplicationsSummary,
	AuthStatus,
	BenchmarkResult,
	ChatMessage,
	ChatStreamEvent,
	ClaudeSetupState,
	CloudModelOption,
	CoverLetter,
	FilterSessionConfirm,
	LLMDeploymentWrite,
	LocalSetupState,
	NewFilterSession,
	OrchestratorStatus,
	PullProgress,
	RateLimitsBudget,
	SearchData,
	SearchHistory,
	SecretStorage,
	Settings,
	SettingsWrite,
	SetupState,
	SummaryScope,
	Vacancy,
	VacancyListPage,
	VacancyStatusFilter,
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

type QueryParams = Record<
	string,
	string | number | readonly string[] | undefined
>;

function qs(params: QueryParams): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined) continue;
		if (Array.isArray(value)) {
			for (const item of value) search.append(key, item);
		} else {
			search.append(key, String(value));
		}
	}
	const encoded = search.toString();
	return encoded ? `?${encoded}` : "";
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
		} catch {}
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
		} catch {}
		throw new APIError(res.status, formatErrorDetail(parsed.detail));
	}
	return JSON.parse(data) as T;
}

async function* streamSSE<T>(
	url: string,
	init: RequestInit,
): AsyncGenerator<T> {
	const res = await fetch(url, {
		...init,
		headers: { "Content-Type": "application/json", ...init.headers },
	});
	if (!res.ok || res.body === null) {
		throw new APIError(res.status, "Failed to open stream");
	}
	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		let boundary = buffer.indexOf("\n\n");
		while (boundary !== -1) {
			const frame = buffer.slice(0, boundary);
			buffer = buffer.slice(boundary + 2);
			const dataLine = frame
				.split("\n")
				.find((line) => line.startsWith("data:"));
			if (dataLine) {
				const payload = dataLine.slice(5).trim();
				if (payload) yield JSON.parse(payload) as T;
			}
			boundary = buffer.indexOf("\n\n");
		}
	}
}

async function* streamChat(
	vacancyId: number,
	message: string,
): AsyncGenerator<ChatStreamEvent> {
	const url = `http://${BASE_IP}:${BASE_PORT}/api/v1/vacancies/${vacancyId}/application/chat`;
	logger.info(`Opening chat stream to "${url}"`);
	yield* streamSSE<ChatStreamEvent>(url, {
		method: "POST",
		body: JSON.stringify({ message }),
	});
}

type PullFrame = PullProgress | { type: "error"; detail: string };

async function* streamPull(): AsyncGenerator<PullProgress> {
	const url = `http://${BASE_IP}:${BASE_PORT}/api/v1/setup/pull`;
	for await (const frame of streamSSE<PullFrame>(url, { method: "POST" })) {
		if ("type" in frame && frame.type === "error") {
			throw new APIError(500, frame.detail);
		}
		yield frame as PullProgress;
	}
}

export const API = {
	auth: {
		status: () => api<AuthStatus>("auth/status"),
		signIn: () => api<AuthStatus>("auth/sign-in", { method: "POST" }),
		signInCancel: () =>
			api<AuthStatus>("auth/sign-in/cancel", { method: "POST" }),
		signOut: () => api<AuthStatus>("auth/sign-out", { method: "POST" }),
	},
	applications: {
		summary: (scope: SummaryScope = "all") =>
			api<ApplicationsSummary>(`applications/summary?search_id=${scope}`),
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
		history: {
			list: () => api<SearchHistory[]>("search/history"),
		},
	},
	vacancies: {
		list: () => api<Vacancy[]>("vacancies/"),
		get: (vacancyId: number) => api<Vacancy>(`vacancies/${vacancyId}`),
		listAll: (opts?: {
			statuses?: readonly VacancyStatusFilter[];
			search?: string;
			limit?: number;
			offset?: number;
		}) =>
			api<VacancyListPage>(
				`vacancies/all${qs({
					status: opts?.statuses,
					q: opts?.search,
					limit: opts?.limit,
					offset: opts?.offset,
				})}`,
			),
	},
	application: {
		get: (vacancyId: number) =>
			api404Null<ApplicationDetail>(`vacancies/${vacancyId}/application`),
		letters: (vacancyId: number) =>
			api<CoverLetter[]>(`vacancies/${vacancyId}/application/letters`),
		generate: (vacancyId: number) =>
			api<ApplicationDetail>(`vacancies/${vacancyId}/application/generate`, {
				method: "POST",
			}),
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
		chat: {
			list: (vacancyId: number) =>
				api<ChatMessage[]>(`vacancies/${vacancyId}/application/chat`),
			stream: (vacancyId: number, message: string) =>
				streamChat(vacancyId, message),
		},
	},
	settings: {
		get: () => api<Settings>("settings"),
		update: (body: SettingsWrite) =>
			api<Settings>("settings", {
				method: "PUT",
				body: JSON.stringify(body),
			}),
	},
	system: {
		rateLimits: () => api<RateLimitsBudget>("system/rate-limits"),
		aiHealth: () => api<{ status: string }>("system/ai/health"),
		secretStorage: () => api<SecretStorage>("system/secret-storage"),
		orchestrator: {
			status: () => api<OrchestratorStatus>("system/orchestrator/status"),
			resume: () =>
				api<APIResponse>("system/orchestrator/resume", { method: "POST" }),
		},
	},
	setup: {
		state: () => api<SetupState>("setup/state"),
		local: () => api<LocalSetupState>("setup/local"),
		claude: () => api<ClaudeSetupState>("setup/claude"),
		cloudModels: () => api<CloudModelOption[]>("setup/cloud-models"),
		pull: () => streamPull(),
		trial: (deployment: LLMDeploymentWrite, deadlineSec: number) =>
			api<BenchmarkResult>("setup/trial", {
				method: "POST",
				body: JSON.stringify({ deployment, deadline_sec: deadlineSec }),
			}),
		deployment: (body: LLMDeploymentWrite) =>
			api<Settings>("setup/deployment", {
				method: "POST",
				body: JSON.stringify(body),
			}),
	},
} as const;
