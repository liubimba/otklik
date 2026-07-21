import { getLogger } from "$lib/log";
import { invoke } from "@tauri-apps/api/core";
import { relaunch } from "@tauri-apps/plugin-process";
import { type Update, check } from "@tauri-apps/plugin-updater";

const logger = getLogger("Updater");

const EMPTY_FEED = [
	"could not fetch a valid release json",
	"did not respond with a successful status code",
];

function isEmptyFeed(message: string): boolean {
	const lowered = message.toLowerCase();
	return EMPTY_FEED.some((signature) => lowered.includes(signature));
}

class Updater {
	available = $state<Update | null>(null);
	checking = $state(false);
	installing = $state(false);
	error = $state<string | null>(null);

	async check(): Promise<boolean> {
		if (this.checking || this.installing) return false;
		this.checking = true;
		this.error = null;
		try {
			const update = await check();
			if (update) {
				this.available = update;
				return true;
			}
			return false;
		} catch (e) {
			const message = e instanceof Error ? e.message : String(e);
			if (isEmptyFeed(message)) {
				logger.info(`No release feed published yet: ${message}`);
				return false;
			}
			this.error = message;
			return false;
		} finally {
			this.checking = false;
		}
	}

	async install(): Promise<void> {
		if (!this.available || this.installing) return;
		this.installing = true;
		this.error = null;
		try {
			await this.available.download();
			await invoke("shutdown_backend");
			await this.available.install();
			await relaunch();
		} catch (e) {
			this.error = e instanceof Error ? e.message : String(e);
			this.installing = false;
		}
	}

	dismiss(): void {
		if (this.installing) return;
		this.available = null;
		this.error = null;
	}
}

export const updater = new Updater();
