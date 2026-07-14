import { API } from "$lib/api/client";
import type { LLMDeployment, SetupState } from "$lib/api/types";
import { getLogger } from "$lib/log";

const OLLAMA_HOST = "http://localhost:11434";
const logger = getLogger("SetupViewModel");

export type SetupScreen =
	| "checking"
	| "weak-hardware"
	| "ollama-missing"
	| "ollama-stopped"
	| "pull"
	| "benchmark"
	| "done"
	| "too-slow"
	| "error";

/**
 * Машина состояний шага «локальная модель».
 *
 * Слабое железо не качает 4.7 ГБ, чтобы потом узнать, что оно их не тянет:
 * пре-фильтр по RAM и ядрам отсекает его раньше ("weak-hardware"). На
 * сильной машине вердикт выносит не эвристика, а секундомер — один
 * настоящий замер ("benchmark" → "done" | "too-slow").
 */
export class SetupViewModel {
	#state = $state<SetupState | null>(null);
	#screen = $state<SetupScreen>("checking");
	#percent = $state(0);
	#seconds = $state(0);
	#letter = $state<string | null>(null);
	#error = $state<string | null>(null);
	#isPulling = $state(false);

	get screen(): SetupScreen {
		return this.#screen;
	}
	get percent(): number {
		return this.#percent;
	}
	/** Идёт ли сейчас загрузка модели — кнопка «Установить модель» смотрит сюда,
	 * чтобы не дать запустить вторую параллельную загрузку. */
	get isPulling(): boolean {
		return this.#isPulling;
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
	get localModel(): string {
		return this.#state?.local_model ?? "";
	}
	get cloudModel(): string {
		return this.#state?.cloud_model ?? "";
	}

	/** Перечитать состояние с бэкенда — «Проверить снова». */
	async refresh(): Promise<void> {
		this.#screen = "checking";
		this.#error = null;
		try {
			const state = await API.setup.state();
			this.#state = state;
			this.#screen = this.#screenAfterHardwareCheck(state);
			if (this.#screen === "benchmark") await this.runBenchmark();
		} catch (error) {
			this.#fail(error);
		}
	}

	/** Загрузка модели + автоматический переход к замеру. */
	async pullModel(): Promise<void> {
		if (this.#isPulling) return; // вторая загрузка поверх первой не запускается
		this.#screen = "pull";
		this.#percent = 0;
		this.#isPulling = true;
		try {
			for await (const progress of API.setup.pull()) {
				this.#percent = progress.percent;
			}
			await this.runBenchmark();
		} catch (error) {
			// Провал стрима не имеет права оставить полосу прогресса висящей
			// на последнем проценте — это отдельное явное состояние ошибки.
			this.#fail(error);
		} finally {
			this.#isPulling = false;
		}
	}

	async runBenchmark(): Promise<void> {
		this.#screen = "benchmark";
		try {
			const result = await API.setup.benchmark();
			this.#seconds = result.seconds;
			this.#letter = result.letter;
			if (!result.passed) {
				// Провал по времени — это НЕ ошибка, а развилка с выбором:
				// deployment не пишем, пока пользователь не решит сам.
				this.#screen = "too-slow";
				return;
			}
			await this.#writeLocalDeployment();
		} catch (error) {
			this.#fail(error);
		}
	}

	/** Слабое железо, но пользователь всё равно хочет локальную модель. */
	async useLocalAnyway(): Promise<void> {
		if (this.#state === null) return;
		// Дальше решает уже реальное состояние Ollama на машине, а не эвристика
		// по железу — та своё дело сделала (отсекла бы качание модели).
		this.#screen = this.#screenForOllama(this.#state);
		if (this.#screen === "benchmark") await this.runBenchmark();
	}

	/** Замер провалился («too-slow»), но пользователь готов ждать. */
	async keepLocal(): Promise<void> {
		try {
			await this.#writeLocalDeployment();
		} catch (error) {
			this.#fail(error);
		}
	}

	async #writeLocalDeployment(): Promise<void> {
		const deployment: LLMDeployment = {
			model: this.#state?.local_model ?? "",
			api_base: OLLAMA_HOST,
			api_key: null,
		};
		await API.setup.deployment(deployment);
		this.#screen = "done";
	}

	// Модель уже настроена — шаг пройден, гонять замер и качать 4.7 ГБ второй
	// раз незачем (P0-1). Иначе слабое железо уходит на развилку, минуя
	// проверку Ollama, — ничего качать для неё смысла нет.
	#screenAfterHardwareCheck(state: SetupState): SetupScreen {
		if (state.has_deployment) return "done";
		if (state.hardware.tier === "weak") return "weak-hardware";
		return this.#screenForOllama(state);
	}

	#screenForOllama(state: SetupState): SetupScreen {
		switch (state.ollama) {
			case "not_installed":
				return "ollama-missing";
			case "not_running":
				return "ollama-stopped";
			case "model_missing":
				return "pull";
			case "ready":
				return "benchmark";
		}
	}

	#fail(error: unknown): void {
		const message = error instanceof Error ? error.message : String(error);
		logger.error(`Setup step failed: ${message}`);
		this.#error = message;
		this.#screen = "error";
	}
}
