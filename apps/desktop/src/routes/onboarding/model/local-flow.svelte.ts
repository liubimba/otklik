import { API } from "$lib/api/client";
import type { LLMDeployment, LocalSetupState, Settings } from "$lib/api/types";
import { getLogger } from "$lib/log";

const OLLAMA_HOST = "http://localhost:11434";
const LOCAL_TRIAL_DEADLINE_SEC = 45;
const logger = getLogger("LocalFlow");

export type LocalScreen =
	| "checking"
	| "ollama-missing"
	| "ollama-stopped"
	| "local-select"
	| "pull"
	| "benchmark"
	| "done"
	| "too-slow"
	| "error";

/**
 * Машина состояний локального пути онбординга: проверка Ollama → выбор из
 * уже стянутых моделей ИЛИ загрузка рекомендованной → замер → deployment.
 * Deployment пишется только после успешного замера (или явного «остаться»
 * с экрана too-slow) — провал по дедлайну оставляет развилку, ничего не
 * записывая (см. Task 6: POST /setup/deployment primary-first).
 */
export class LocalFlow {
	#state = $state<LocalSetupState | null>(null);
	#screen = $state<LocalScreen>("checking");
	#percent = $state(0);
	#seconds = $state(0);
	#letter = $state<string | null>(null);
	#error = $state<string | null>(null);
	#isPulling = $state(false);
	#chosenTag = "";
	#onDeploymentSaved: (settings: Settings) => void;

	constructor(onDeploymentSaved: (settings: Settings) => void = () => {}) {
		this.#onDeploymentSaved = onDeploymentSaved;
	}

	get screen(): LocalScreen {
		return this.#screen;
	}
	get percent(): number {
		return this.#percent;
	}
	get seconds(): number {
		return this.#seconds;
	}
	get letter(): string | null {
		return this.#letter;
	}
	get errorMessage(): string | null {
		return this.#error;
	}
	/** Идёт ли сейчас загрузка модели — кнопка «Установить модель» смотрит сюда,
	 * чтобы не дать запустить вторую параллельную загрузку. */
	get isPulling(): boolean {
		return this.#isPulling;
	}
	get installedModels(): string[] {
		return this.#state?.installed_models ?? [];
	}
	get recommendedTag(): string {
		return this.#state?.recommended_tag ?? "";
	}

	/** Перечитать состояние с бэкенда — «Проверить снова». */
	async refresh(): Promise<void> {
		this.#screen = "checking";
		this.#error = null;
		try {
			const state = await API.setup.local();
			this.#state = state;
			this.#screen = this.#screenForOllama(state);
		} catch (error) {
			this.#fail(error);
		}
	}

	/** Замер уже стянутой модели, выбранной пользователем из списка. */
	async selectInstalled(tag: string): Promise<void> {
		this.#chosenTag = tag;
		await this.#benchmark(`ollama_chat/${tag}`);
	}

	/** Загрузка рекомендованной модели + автоматический переход к замеру. */
	async installRecommended(): Promise<void> {
		if (this.#isPulling) return; // вторая загрузка поверх первой не запускается
		this.#chosenTag = this.recommendedTag;
		this.#screen = "pull";
		this.#percent = 0;
		this.#isPulling = true;
		try {
			for await (const progress of API.setup.pull()) {
				this.#percent = progress.percent;
			}
			await this.#benchmark(`ollama_chat/${this.#chosenTag}`);
		} catch (error) {
			// Провал стрима не имеет права оставить полосу прогресса висящей
			// на последнем проценте — это отдельное явное состояние ошибки.
			this.#fail(error);
		} finally {
			this.#isPulling = false;
		}
	}

	/** Замер провалился («too-slow»), но пользователь готов ждать. */
	async keepLocal(): Promise<void> {
		try {
			await this.#writeDeployment();
		} catch (error) {
			this.#fail(error);
		}
	}

	async #benchmark(model: string): Promise<void> {
		this.#screen = "benchmark";
		try {
			const deployment: LLMDeployment = {
				model,
				api_base: OLLAMA_HOST,
				api_key: null,
			};
			const result = await API.setup.trial(
				deployment,
				LOCAL_TRIAL_DEADLINE_SEC,
			);
			this.#seconds = result.seconds;
			this.#letter = result.letter;
			if (!result.passed) {
				if (result.failure_reason === "model_error") {
					// Модель не ответила вовсе — это не про скорость, показывать
					// «медленно» здесь нельзя: пользователь нажмёт «остаться на
					// локальной» и мы запишем deployment, который ни разу не
					// сработал. Это настоящая ошибка — экран error, не развилка.
					this.#fail(result.error ?? "model_error");
					return;
				}
				// Провал по времени — это НЕ ошибка, а развилка с выбором:
				// deployment не пишем, пока пользователь не решит сам.
				this.#screen = "too-slow";
				return;
			}
			await this.#writeDeployment();
		} catch (error) {
			this.#fail(error);
		}
	}

	async #writeDeployment(): Promise<void> {
		const deployment: LLMDeployment = {
			model: `ollama_chat/${this.#chosenTag}`,
			api_base: OLLAMA_HOST,
			api_key: null,
		};
		const saved = await API.setup.deployment(deployment);
		this.#onDeploymentSaved(saved);
		this.#screen = "done";
	}

	#screenForOllama(state: LocalSetupState): LocalScreen {
		switch (state.ollama_state) {
			case "not_installed":
				return "ollama-missing";
			case "not_running":
				return "ollama-stopped";
			default:
				return "local-select";
		}
	}

	#fail(error: unknown): void {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Local setup step failed: ${message}`);
		this.#error = message;
		this.#screen = "error";
	}
}
