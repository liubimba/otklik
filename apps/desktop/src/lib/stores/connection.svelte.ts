export type ConnectionState = "connecting" | "online" | "offline";

/**
 * Жив ли бэкенд. Единственный честный источник этого сигнала — жизненный цикл
 * WS (`lib/api/events.ts`): только он знает, отвечает ли сервер. onOpen → online,
 * обрыв или неудачная попытка открыть → offline.
 *
 * Стартовое состояние — "connecting", а не "offline": на обычном запуске сокет
 * подключается за доли секунды, и мигать «нет связи» на каждом старте нельзя.
 * Баннер и офлайн-состояние профиля смотрят на `isOffline`, поэтому "connecting"
 * молчит, пока не придёт первый настоящий вердикт.
 */
export class ConnectionStore {
	#state = $state<ConnectionState>("connecting");

	get state(): ConnectionState {
		return this.#state;
	}
	get isOnline(): boolean {
		return this.#state === "online";
	}
	get isOffline(): boolean {
		return this.#state === "offline";
	}

	online(): void {
		this.#state = "online";
	}
	offline(): void {
		this.#state = "offline";
	}
}

export const connection = new ConnectionStore();
