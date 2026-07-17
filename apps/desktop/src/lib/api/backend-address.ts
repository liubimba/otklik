import { invoke } from "@tauri-apps/api/core";

let cached: Promise<string> | null = null;

export function resetBackendAddress(): void {
	cached = null;
}

export function backendOrigin(): Promise<string> {
	if (cached === null) {
		cached = invoke<number>("get_backend_port")
			.then((port) => `127.0.0.1:${port}`)
			.catch((e) => {
				cached = null;
				throw e;
			});
	}
	return cached;
}
