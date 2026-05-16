import { authenticate, getAuthStatus } from "$lib/api/client";
import { connectEvents } from "$lib/api/events";
import type { AuthStatus, ServerEvent } from "$lib/api/types";
import { getLogger } from "$lib/log";

function createAuthStore() {
	let state = $state<AuthStatus | null>(null);
	const logger = getLogger("AuthStore");
	let client: WebSocket | null = null;

	async function fetchStatus() {
		logger.info("Fetching authentication status");
		try {
			state = await getAuthStatus();
		} catch (error) {
			logger.error("Failed to fetch auth status:", error);
			state = null;
		}
	}

	async function fetchAuthentication() {
		if (state?.status === "authorizing") {
			logger.warn(
				"Already in the process of authorizing. Skipping new authentication attempt.",
			);
			return;
		}
		if (client == null) {
			client = connectEvents(
				(event: ServerEvent) => {
					if (event.type === "auth_changed") {
						logger.info(
							`Received auth status change event: ${event.data.status}`,
						);
						state = event.data;
					}
				},
				(err) => {
					logger.error(`WebSocket error for auth events: ${err}`);
				},
				() => {
					logger.warn("WebSocket connection closed for auth events");
				},
			);
		}
		logger.info("Starting authentication process");
		try {
			state = await authenticate();
		} catch (error) {
			logger.error("Authentication failed:", error);
			state = null;
		}
	}

	return {
		getState: () => state,
		fetchStatus: fetchStatus,
		fetchAuthentication: fetchAuthentication,
	};
}

export const auth = createAuthStore();
