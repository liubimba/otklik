import { getLogger } from "$lib/log";
import type { AuthStatus } from "./types";
const BASE_IP = import.meta.env.VITE_BACKEND_IP;
const BASE_PORT = import.meta.env.VITE_BACKEND_PORT;
const logger = getLogger("APIClient");

async function api<T>(path: string, init?: RequestInit): Promise<T> {
	const url: string = `http://${BASE_IP}:${BASE_PORT}/api/v1/${path}`;
	logger.info(
		`Making API request to "${url}" with method: ${init?.method || "GET"}`,
	);
	const res = await fetch(url, {
		...init,
	});
	const data = await res.text();
	logger.info(
		`API request to "${url}" returned status: ${res.status}. Response: ${data}`,
	);
	if (!res.ok) {
		throw new Error(`API request "${url}" failed with status: ${res.status}`);
	}
	return JSON.parse(data) as T;
}

export async function getAuthStatus(): Promise<AuthStatus> {
	return api<AuthStatus>("auth/status");
}

export async function authenticate(): Promise<AuthStatus> {
	return api<AuthStatus>("auth", { method: "POST" });
}
