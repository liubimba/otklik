import { API } from "$lib/api/client";
import type { ClaudeModelOption, Settings } from "$lib/api/types";
import { getLogger } from "$lib/log";

const CLAUDE_TRIAL_DEADLINE_SEC = 90;
const logger = getLogger("ClaudeFlow");

export type ClaudeScreen =
	| "checking"
	| "not-installed"
	| "not-authed"
	| "select"
	| "trial"
	| "error";

export class ClaudeFlow {
	#screen = $state<ClaudeScreen>("checking");
	#models = $state<ClaudeModelOption[]>([]);
	#selected = $state<string | null>(null);
	#letter = $state<string | null>(null);
	#seconds = $state(0);
	#error = $state<string | null>(null);
	#isSubmitting = $state(false);
	#onDeploymentSaved: (settings: Settings) => void;

	constructor(onDeploymentSaved: (settings: Settings) => void) {
		this.#onDeploymentSaved = onDeploymentSaved;
	}

	get screen(): ClaudeScreen {
		return this.#screen;
	}
	get models(): ClaudeModelOption[] {
		return this.#models;
	}
	get selected(): string | null {
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

	async load(): Promise<void> {
		this.#screen = "checking";
		this.#error = null;
		try {
			const state = await API.setup.claude();
			this.#models = state.model_options;
			this.#selected = state.default_model;
			if (state.claude_state === "not_installed") {
				this.#screen = "not-installed";
			} else if (state.claude_state === "not_authed") {
				this.#screen = "not-authed";
			} else {
				this.#screen = "select";
			}
		} catch (error) {
			this.#fail(error);
		}
	}

	selectModel(model: string): void {
		this.#selected = model;
	}

	async runTrial(): Promise<boolean> {
		if (this.#selected === null) return false;
		if (this.#isSubmitting) return false;
		this.#isSubmitting = true;
		this.#screen = "trial";
		this.#error = null;
		try {
			const deployment = {
				model: this.#selected,
				api_key: null,
				api_base: null,
			};
			const result = await API.setup.trial(
				deployment,
				CLAUDE_TRIAL_DEADLINE_SEC,
			);
			if (!result.passed) {
				this.#error = result.error ?? "trial failed";
				this.#screen = "select";
				return false;
			}
			this.#letter = result.letter;
			this.#seconds = result.seconds;
			const saved = await API.setup.deployment(deployment);
			this.#onDeploymentSaved(saved);
			return true;
		} catch (error) {
			this.#error = error instanceof Error ? error.message : String(error);
			this.#screen = "select";
			return false;
		} finally {
			this.#isSubmitting = false;
		}
	}

	#fail(error: unknown): void {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Claude setup failed: ${message}`);
		this.#error = message;
		this.#screen = "error";
	}
}
