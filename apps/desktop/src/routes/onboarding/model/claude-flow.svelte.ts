import { API } from "$lib/api/client";
import type { ClaudeModelOption, Settings } from "$lib/api/types";
import { getLogger } from "$lib/log";

// Claude на подписке пишет медленнее локальной болталки, но качество выше —
// даём вдвое больше времени, чем облаку (60с), чтобы не резать по дедлайну.
const CLAUDE_TRIAL_DEADLINE_SEC = 90;
const logger = getLogger("ClaudeFlow");

export type ClaudeScreen =
	| "checking"
	| "not-installed"
	| "not-authed"
	| "select"
	| "trial"
	| "error";

/**
 * Машина состояний пути «Claude по подписке»: детект CLI → выбор модели →
 * пробное письмо → deployment. Deployment пишется только после успешного
 * trial'а. Ключ не нужен — auth живёт в самом CLI (`claude -p`), мы его не
 * трогаем; deployment у Claude без api_key/api_base (дискриминатор — префикс
 * модели `claude-code/`).
 */
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

	/** Спрашивает бэкенд про состояние CLI и приземляется на нужный экран. */
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

	/**
	 * Пробное письмо на выбранной модели Claude. Успех — пишет deployment и
	 * зовёт onDeploymentSaved (прогрев кэша Настроек). Провал (любой
	 * passed=false, в т.ч. протухший токен → model_error) оставляет на
	 * "select" с сообщением, ничего не записывая.
	 */
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
