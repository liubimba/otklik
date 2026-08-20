import { type UnlistenFn, listen } from "@tauri-apps/api/event";

export const BACKEND_EXIT_EVENT = "backend://exited";

export interface BackendExitPayload {
	code: number | null;
	stderr: string;
}

export function onBackendExit(
	handler: (detail?: string) => void,
): Promise<UnlistenFn> {
	return listen<BackendExitPayload>(BACKEND_EXIT_EVENT, (event) => {
		handler(event.payload.stderr || undefined);
	});
}
