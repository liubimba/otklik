import { getLogger } from "$lib/log";
import { backendOrigin } from "./backend-address";
import type { ServerEvent } from "./types";

export interface ReconnectOptions {
	initialDelay?: number;
	maxDelay?: number;
	backoffFactor?: number;
	maxAttempts?: number;
}

export class EventsWebSocket {
	private ws: WebSocket | null = null;
	private logger = getLogger(EventsWebSocket.name);
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

	private url = "";
	private readonly options: Required<ReconnectOptions>;
	private closed = false;
	private currentDelay: number;
	private attempts = 0;

	constructor(
		private readonly onEvent: (event: ServerEvent) => void,
		private readonly onError?: (event: Event) => void,
		private readonly onClose?: () => void,
		options: ReconnectOptions = {},
		private readonly onOpen?: () => void,
		private readonly onDisconnect?: () => void,
	) {
		this.options = {
			initialDelay: options.initialDelay ?? 1_000,
			maxDelay: options.maxDelay ?? 30_000,
			backoffFactor: options.backoffFactor ?? 2,
			maxAttempts: options.maxAttempts ?? Number.POSITIVE_INFINITY,
		};
		this.currentDelay = this.options.initialDelay;
	}

	public close(): void {
		this.closed = true;
		this.ws?.close();
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		this.logger.info(`Closed connection for server events (url=${this.url})`);
	}

	public connect(): void {
		if (this.closed) {
			return;
		}
		void this.openSocket();
	}

	private async openSocket(): Promise<void> {
		try {
			this.url = `ws://${await backendOrigin()}/ws/events`;
		} catch (error) {
			this.logger.error(
				`Cannot resolve the backend port from Tauri: ${
					error instanceof Error ? error.message : String(error)
				}. The sidecar is probably still starting.`,
			);
			this.ws = null;
			this.onError?.(new Event("error"));
			this.onDisconnect?.();
			this.scheduleReconnect();
			return;
		}
		if (this.closed) {
			return;
		}
		this.logger.info(
			`Connecting to ${this.url}${this.attempts > 0 ? ` (attempt #${this.attempts + 1})` : ""}`,
		);

		try {
			this.ws = new WebSocket(this.url);
		} catch (error) {
			this.logger.error(
				`Cannot open the server-events socket (url=${this.url}): ${
					error instanceof Error ? error.message : String(error)
				}`,
			);
			this.ws = null;
			this.onError?.(new Event("error"));
			this.onDisconnect?.();
			return;
		}

		this.ws.onopen = () => {
			this.logger.info("WebSocket connection established for server events");
			this.resetBackoff();
			this.onOpen?.();
		};
		this.ws.onclose = (event) => {
			this.logger.info(
				`WebSocket connection closed for server events (code = ${event.code}, wasClosing = ${event.wasClean})`,
			);
			if (!this.closed) {
				this.onDisconnect?.();
				this.scheduleReconnect();
			} else {
				this.onClose?.();
			}
		};
		this.ws.onmessage = (message: MessageEvent) => {
			try {
				const event: ServerEvent = JSON.parse(message.data);
				this.onEvent(event);
			} catch (err) {
				this.logger.error(
					`Failed to parse server event message. Error: ${err}`,
				);
			}
		};
		this.ws.onerror = (err) => {
			this.logger.error(
				`WebSocker error for server events. Error: ${String(err)}`,
			);
			this.onError?.(err);
		};
	}

	private resetBackoff(): void {
		this.attempts = 0;
		this.currentDelay = this.options.initialDelay;
	}

	private scheduleReconnect(): void {
		const { maxAttempts, maxDelay, backoffFactor } = this.options;

		if (this.attempts >= maxAttempts) {
			this.logger.error(
				`Max reconnect attempts (${maxAttempts}) reached. Giving up`,
			);
			this.closed = true;
			this.onClose?.();
			return;
		}

		this.attempts++;
		const delay = this.currentDelay;

		this.logger.info(
			`Reconnection in ${delay} ms (attempt #${this.attempts}${maxAttempts !== Number.POSITIVE_INFINITY ? `/${maxAttempts}` : ""})`,
		);

		this.reconnectTimer = setTimeout(() => {
			this.reconnectTimer = null;
			this.connect();
		}, delay);

		this.currentDelay = Math.min(delay * backoffFactor, maxDelay);
	}
}
