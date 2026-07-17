import { relaunch } from "@tauri-apps/plugin-process";
import { type Update, check } from "@tauri-apps/plugin-updater";

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
			this.error = e instanceof Error ? e.message : String(e);
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
			await this.available.downloadAndInstall();
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
