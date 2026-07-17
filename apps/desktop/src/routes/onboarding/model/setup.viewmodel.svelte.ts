import { API } from "$lib/api/client";
import type { Settings } from "$lib/api/types";
import { getLogger } from "$lib/log";
import { ClaudeFlow } from "./claude-flow.svelte";
import { CloudFlow } from "./cloud-flow.svelte";
import { LocalFlow } from "./local-flow.svelte";

const logger = getLogger("SetupViewModel");

export type SetupPath = "choose" | "local" | "cloud" | "claude";

export class SetupViewModel {
	#path = $state<SetupPath>("choose");
	#hardwareWeak = $state(false);
	#currentModel = $state<string | null>(null);
	#claudeAvailable = $state(false);
	readonly local: LocalFlow;
	readonly cloud: CloudFlow;
	readonly claude: ClaudeFlow;

	constructor(onDeploymentSaved: (settings: Settings) => void = () => {}) {
		this.local = new LocalFlow(onDeploymentSaved);
		this.cloud = new CloudFlow(onDeploymentSaved);
		this.claude = new ClaudeFlow(onDeploymentSaved);
	}

	get path(): SetupPath {
		return this.#path;
	}
	get hardwareWeak(): boolean {
		return this.#hardwareWeak;
	}
	get currentModel(): string | null {
		return this.#currentModel;
	}
	get claudeAvailable(): boolean {
		return this.#claudeAvailable;
	}

	async init(): Promise<void> {
		try {
			const state = await API.setup.state();
			this.#hardwareWeak = state.hardware.tier === "weak";
			this.#currentModel = state.has_deployment ? state.local_model : null;
			this.#claudeAvailable = state.claude_available;
		} catch (error) {
			logger.error(
				`Setup init failed: ${error instanceof Error ? error.message : String(error)}`,
			);
		}
	}

	async chooseLocal(): Promise<void> {
		this.#path = "local";
		await this.local.refresh();
	}

	async chooseCloud(): Promise<void> {
		this.#path = "cloud";
		await this.cloud.load();
	}

	async chooseClaude(): Promise<void> {
		this.#path = "claude";
		await this.claude.load();
	}

	back(): void {
		this.#path = "choose";
	}
}
