export type ConnectionState = "connecting" | "online" | "offline" | "failed";

export class ConnectionStore {
	#state = $state<ConnectionState>("connecting");
	#detail = $state<string | null>(null);

	get state(): ConnectionState {
		return this.#state;
	}
	get isOnline(): boolean {
		return this.#state === "online";
	}
	get isOffline(): boolean {
		return this.#state === "offline";
	}
	get isFailed(): boolean {
		return this.#state === "failed";
	}
	get detail(): string | null {
		return this.#detail;
	}

	online(): void {
		this.#state = "online";
	}
	offline(): void {
		this.#state = "offline";
	}
	failed(detail?: string): void {
		this.#state = "failed";
		this.#detail = detail ?? null;
	}
}

export const connection = new ConnectionStore();
