import { API } from "$lib/api/client";
import { getLogger } from "$lib/log";

export type BrowserScreen = "checking" | "downloading" | "ready" | "error";

const logger = getLogger("BrowserFlow");

export class BrowserFlow {
	#screen = $state<BrowserScreen>("checking");
	#percent = $state(0);
	#error = $state<string | null>(null);
	#busy = false;

	get screen(): BrowserScreen {
		return this.#screen;
	}

	get percent(): number {
		return this.#percent;
	}

	get error(): string | null {
		return this.#error;
	}

	async start(): Promise<void> {
		if (this.#busy) return;
		this.#busy = true;
		try {
			const state = await API.setup.state();
			if (state.chromium_installed) {
				this.#screen = "ready";
				return;
			}
			await this.#download();
		} catch (error) {
			this.#fail(error);
		} finally {
			this.#busy = false;
		}
	}

	async retry(): Promise<void> {
		if (this.#busy) return;
		this.#busy = true;
		this.#error = null;
		try {
			await this.#download();
		} catch (error) {
			this.#fail(error);
		} finally {
			this.#busy = false;
		}
	}

	async #download(): Promise<void> {
		this.#screen = "downloading";
		this.#percent = 0;
		for await (const progress of API.setup.chromium()) {
			this.#percent = progress.percent;
		}
		this.#percent = 100;
		this.#screen = "ready";
		logger.info("Chromium is ready");
	}

	#fail(error: unknown): void {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Chromium download failed: ${message}`);
		this.#error = message;
		this.#screen = "error";
	}
}
