import { authenticate, getAuthStatus } from "$lib/api/client";
import type { AuthEvent, AuthStatus } from "$lib/api/types";
import { getLogger } from "$lib/log";

function createAuthStore() {
	let state = $state<AuthStatus | null>(null);
	const logger = getLogger("AuthStore");

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
		logger.info("Starting authentication process");
		try {
			state = await authenticate();
		} catch (error) {
			logger.error("Authentication failed:", error);
			state = null;
		}
	}

	function applyAuthEvent(event: AuthEvent) {
		logger.info(`Received auth status change event: ${event.data.status}`);
		state = event.data;
	}

	return {
		getState: () => state,
		fetchStatus,
		fetchAuthentication,
		applyAuthEvent,
	};
}

export const auth = createAuthStore();
