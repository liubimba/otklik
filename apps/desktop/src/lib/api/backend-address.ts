import { invoke } from "@tauri-apps/api/core";

const READY_TIMEOUT_MS = 90_000;
const READY_POLL_MS = 250;

let cached: Promise<string> | null = null;

export function resetBackendAddress(): void {
	cached = null;
}

const sleep = (ms: number): Promise<void> =>
	new Promise((resolve) => setTimeout(resolve, ms));

async function waitUntilReady(origin: string): Promise<string> {
	const deadline = Date.now() + READY_TIMEOUT_MS;
	let lastError: unknown = null;
	while (Date.now() < deadline) {
		try {
			const response = await fetch(`http://${origin}/api/v1/system/health`);
			if (response.ok) return origin;
			lastError = new Error(`health returned ${response.status}`);
		} catch (error) {
			lastError = error;
		}
		await sleep(READY_POLL_MS);
	}
	throw new Error(
		`Backend did not become ready on ${origin}: ${
			lastError instanceof Error ? lastError.message : String(lastError)
		}`,
	);
}

export function backendOrigin(): Promise<string> {
	if (cached === null) {
		cached = invoke<number>("get_backend_port")
			.then((port) => waitUntilReady(`127.0.0.1:${port}`))
			.catch((e) => {
				cached = null;
				throw e;
			});
	}
	return cached;
}
