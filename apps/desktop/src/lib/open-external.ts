import { getLogger } from "$lib/log";
import { openUrl } from "@tauri-apps/plugin-opener";

const logger = getLogger("openExternal");

export async function openExternal(url: string): Promise<void> {
	try {
		await openUrl(url);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Failed to open ${url}: ${message}`);
	}
}
