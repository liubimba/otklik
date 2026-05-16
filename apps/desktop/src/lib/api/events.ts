import { getLogger } from "$lib/log";
import type { ServerEvent } from "./types";
const BASE_IP = import.meta.env.VITE_BACKEND_IP;
const BASE_PORT = import.meta.env.VITE_BACKEND_PORT;

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
