import { getLogger } from "$lib/log";
import type { ServerEvent } from "./types";

const BASE_IP = import.meta.env.VITE_BACKEND_IP;
const BASE_PORT = import.meta.env.VITE_BACKEND_PORT;

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

	private readonly url: string;
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
	) {
		// onOpen intentionally trails `options` (which carries a default) — every
		// existing call site passes it positionally, so re-ordering would force a
		// churn edit at each one for no behavioural gain.
		this.url = `ws://${BASE_IP}:${BASE_PORT}/ws/events`;
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
		this.logger.info(
			`Connecting to ${this.url}${this.attempts > 0 ? ` (attempt #${this.attempts + 1})` : ""}`,
		);

		// The WebSocket constructor THROWS on a malformed url — and `connect()` is
		// called from an `$effect` in the root layout, so that throw lands inside
		// Svelte's mount flush and aborts the scheduler: onMount never runs,
		// reactivity stops flushing, and SvelteKit's router never initialises, so
		// every link degrades to a full page load. The app renders, looks alive and
		// is quietly dead. That is exactly what a missing VITE_BACKEND_IP/PORT did
		// (`ws://undefined:undefined/ws/events`).
		//
		// A connection we cannot open is a degraded backend, not a reason to kill
		// the UI. Report it and let the caller decide.
		try {
			this.ws = new WebSocket(this.url);
		} catch (error) {
			this.logger.error(
				`Cannot open the server-events socket (url=${this.url}): ${
					error instanceof Error ? error.message : String(error)
				}. Is VITE_BACKEND_IP/VITE_BACKEND_PORT set? See apps/desktop/.env.example`,
			);
			this.ws = null;
			this.onError?.(new Event("error"));
			return;
		}

		this.ws.onopen = () => {
			this.logger.info("WebSocket connection established for server events");
			this.resetBackoff();
			// Every (re)connect is a real "may have missed events" signal — the
			// server has no replay buffer, so anything published while we were
			// down (or during the pre-boot connect race) is simply gone. Give
			// the caller a chance to resync state that only WS events refresh.
			this.onOpen?.();
		};
		this.ws.onclose = (event) => {
			this.logger.info(
				`WebSocket connection closed for server events (code = ${event.code}, wasClosing = ${event.wasClean})`,
			);
			if (!this.closed) {
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

export function connectEvents(
	onEvent: (event: ServerEvent) => void,
	onError?: (event: Event) => void,
	onClose?: () => void,
): WebSocket {
	const logger = getLogger("api/events");
	const ws = new WebSocket(`ws://${BASE_IP}:${BASE_PORT}/ws/events`);
	ws.onopen = () => {
		logger.info("WebSocket connection established for server events");
	};
	ws.onclose = () => {
		logger.info("WebSocket connection closed for server events");
		onClose?.();
	};
	ws.onerror = (err: Event) => {
		logger.error(`WebSocket error for server events. Error: ${err}`);
		onError?.(err);
	};
	ws.onmessage = (message) => {
		try {
			const event: ServerEvent = JSON.parse(message.data);
			onEvent(event);
		} catch (err) {
			logger.error(`Failed to parse server event message. Error: ${err}`);
		}
	};
	logger.info("Register new WebSocket connection for server events");
	return ws;
}
