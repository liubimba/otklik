import { getLogger } from "$lib/log";
import { APIError } from "./error";
import type {
	APIRequestError,
	APIResponse,
	AuthStatus,
	FilterSessionConfirm,
	NewFilterSession,
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
	const url: string = `http://${BASE_IP}:${BASE_PORT}/api/v1/${path}`;
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

async function apiNullable<T>(
	path: string,
	init?: RequestInit,
): Promise<T | null> {
	const url: string = `http://${BASE_IP}:${BASE_PORT}/api/v1/${path}`;
	logger.info(
		`Making API request to "${url}" with method: ${init?.method || "GET"}`,
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
	if (res.status === 204) {
		return null as T;
	}
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

export async function getAuthStatus(): Promise<AuthStatus> {
	return api<AuthStatus>("auth/status");
}

export async function authenticate(): Promise<AuthStatus> {
	return api<AuthStatus>("auth", { method: "POST" });
}

export async function getVacancies(): Promise<Vacancy[]> {
	return api<Vacancy[]>("vacancies/");
}

export async function getSettings(): Promise<Settings> {
	return api<Settings>("settings");
}

export async function startFilterSession(): Promise<NewFilterSession> {
	return api<NewFilterSession>("search/picker/new", { method: "POST" });
}

export async function confirmFilterSession(
	session_id: string,
): Promise<FilterSessionConfirm> {
	return api<FilterSessionConfirm>(`search/picker/${session_id}/confirm`, {
		method: "POST",
	});
}

export async function cancelFilterSession(
	session_id: string,
): Promise<APIResponse> {
	return api<APIResponse>(`search/picker/${session_id}/cancel`, {
		method: "POST",
	});
}

export async function startSearchVacancies(
	url: string,
	max_pages?: number | null,
	max_vacancies?: number | null,
): Promise<SearchData> {
	return await api<SearchData>("search/vacancies/new", {
		method: "POST",
		body: JSON.stringify({
			url: url,
			max_pages: max_pages,
			max_vacancies: max_vacancies,
		}),
	});
}

export async function getCurrentSearchVacancies() {
	return await apiNullable<SearchData>("search/vacancies/current");
}

export async function deleteSearchVacancies(search_id: string) {
	await api<APIResponse>(`search/vacancies/${search_id}`, { method: "DELETE" });
}

export async function putSettings(body: Settings): Promise<Settings> {
	return api<Settings>("settings", {
		method: "PUT",
		body: JSON.stringify(body),
	});
}
