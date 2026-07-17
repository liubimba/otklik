import { API } from "$lib/api/client";
import type { CloudModelOption, Settings } from "$lib/api/types";
import { getLogger } from "$lib/log";

const CLOUD_TRIAL_DEADLINE_SEC = 60;
const logger = getLogger("CloudFlow");

export type CloudScreen = "select" | "key" | "trial" | "error";

export class CloudFlow {
	#screen = $state<CloudScreen>("select");
	#models = $state<CloudModelOption[]>([]);
	#query = $state("");
	#selected = $state<CloudModelOption | null>(null);
	#letter = $state<string | null>(null);
	#seconds = $state(0);
	#error = $state<string | null>(null);
	#isSubmitting = $state(false);
	#onDeploymentSaved: (settings: Settings) => void;

	constructor(onDeploymentSaved: (settings: Settings) => void) {
		this.#onDeploymentSaved = onDeploymentSaved;
	}

	get screen(): CloudScreen {
		return this.#screen;
	}
	get models(): CloudModelOption[] {
		return this.#models;
	}
	get query(): string {
		return this.#query;
	}
	get selected(): CloudModelOption | null {
		return this.#selected;
	}
	get letter(): string | null {
		return this.#letter;
	}
	get seconds(): number {
		return this.#seconds;
	}
	get errorMessage(): string | null {
		return this.#error;
	}
	get isSubmitting(): boolean {
		return this.#isSubmitting;
	}

	get filtered(): CloudModelOption[] {
		const q = this.#query.trim().toLowerCase();
		if (!q) return this.#models;
		return this.#models.filter(
			(o) =>
				o.label.toLowerCase().includes(q) ||
				o.provider.toLowerCase().includes(q),
		);
	}

	async load(): Promise<void> {
		try {
			this.#models = await API.setup.cloudModels();
			this.#screen = "select";
		} catch (error) {
			this.#fail(error);
		}
	}

	setQuery(q: string): void {
		this.#query = q;
	}

	choose(option: CloudModelOption): void {
		this.#selected = option;
		this.#error = null;
		this.#screen = "key";
	}

	backToSelect(): void {
		this.#error = null;
		this.#screen = "select";
		this.#selected = null;
		this.#letter = null;
	}

	async submitKey(key: string): Promise<boolean> {
		if (this.#selected === null) return false;
		if (this.#isSubmitting) return false;
		this.#isSubmitting = true;
		this.#screen = "trial";
		this.#error = null;
		try {
			const deployment = { model: this.#selected.model, api_key: key };
			const result = await API.setup.trial(
				deployment,
				CLOUD_TRIAL_DEADLINE_SEC,
			);
			if (!result.passed) {
				this.#error = result.error ?? "trial failed";
				this.#screen = "key";
				return false;
			}
			this.#letter = result.letter;
			this.#seconds = result.seconds;
			const saved = await API.setup.deployment(deployment);
			this.#onDeploymentSaved(saved);
			return true;
		} catch (error) {
			this.#error = error instanceof Error ? error.message : String(error);
			this.#screen = "key";
			return false;
		} finally {
			this.#isSubmitting = false;
		}
	}

	#fail(error: unknown): void {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Cloud setup failed: ${message}`);
		this.#error = message;
		this.#screen = "error";
	}
}
