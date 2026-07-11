import { relaunch } from "@tauri-apps/plugin-process";
import { type Update, check } from "@tauri-apps/plugin-updater";

// Shared update state, driven by both the silent check on startup (in the root
// layout) and the manual "Check for updates" button on the About screen. When
// `available` is non-null, the mounted <UpdateDialog/> reveals itself.
class Updater {
	available = $state<Update | null>(null);
	checking = $state(false);
	installing = $state(false);
	error = $state<string | null>(null);

	/**
	 * Look for an update. Returns true if one was found. Never throws — any
	 * failure (no release feed yet, offline, updater misconfigured) lands in
	 * `error` so callers can stay quiet on startup and surface it on demand.
	 */
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

	/** Download + install the found update, then relaunch into the new version. */
	async install(): Promise<void> {
		if (!this.available || this.installing) return;
		this.installing = true;
		this.error = null;
		try {
			await this.available.downloadAndInstall();
			await relaunch();
		} catch (e) {
			// relaunch() never returns on success, so reaching here means it
			// failed — re-enable the dialog so the user can retry or dismiss.
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
