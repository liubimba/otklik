import { getLogger } from "$lib/log";
import { shell } from "$lib/shell";

const logger = getLogger("openExternal");

export async function openExternal(url: string): Promise<void> {
	try {
		await shell().openExternal(url);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Failed to open ${url}: ${message}`);
	}
}
