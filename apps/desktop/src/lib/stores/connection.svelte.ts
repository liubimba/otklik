export type ConnectionState = "connecting" | "online" | "offline";

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
