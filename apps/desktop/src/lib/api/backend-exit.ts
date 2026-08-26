import { shell } from "$lib/shell";

export const BACKEND_EXIT_EVENT = "backend-exited";

export interface BackendExitPayload {
	code: number | null;
	stderr: string;
}

export function onBackendExit(handler: (detail?: string) => void): () => void {
	return shell().onBackendExit(handler);
}
