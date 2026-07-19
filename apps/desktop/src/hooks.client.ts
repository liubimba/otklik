import { getLogger } from "$lib/log";
import type { HandleClientError } from "@sveltejs/kit";

const logger = getLogger("client");

export const handleError: HandleClientError = ({ error, event }) => {
	const message = error instanceof Error ? error.message : String(error);
	const stack = error instanceof Error ? error.stack : undefined;
	logger.error(
		`Unhandled client error on ${event.url?.pathname ?? "?"}: ${message}${
			stack ? `\n${stack}` : ""
		}`,
	);
	return { message };
};
