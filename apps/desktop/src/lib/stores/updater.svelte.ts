import { getLogger } from "$lib/log";
import { shell } from "$lib/shell";
import type { UpdateInfo } from "$lib/shell-types";

const logger = getLogger("Updater");

class Updater {
	available = $state<UpdateInfo | null>(null);
	checking = $state(false);
	installing = $state(false);
	error = $state<string | null>(null);

	async check(): Promise<boolean> {
		if (this.checking || this.installing) return false;
		this.checking = true;
		this.error = null;
		try {
			const update = await shell().updater.check();
			if (update) {
				this.available = update;
				return true;
			}
			return false;
		} catch (e) {
			this.error = e instanceof Error ? e.message : String(e);
			logger.error(`Update check failed: ${this.error}`);
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
			await shell().updater.install();
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
