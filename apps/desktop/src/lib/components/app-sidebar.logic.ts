import type { AuthStatus } from "$lib/api/types";

export type CellStatus =
	| "loading"
	| "unauthorized"
	| "authorizing"
	| "authorized"
	| "offline";

export function authCellStatus(
	isOffline: boolean,
	data: AuthStatus | undefined,
): CellStatus {
	if (isOffline) return "offline";
	if (!data) return "loading";
	if (data.status === "authorized") return "authorized";
	if (data.status === "authorizing") return "authorizing";
	return "unauthorized";
}

export function badgeCount(
	isOffline: boolean,
	count: number | null,
): number | null {
	return isOffline ? null : count;
}

export async function guardedAuthAction(
	action: () => Promise<unknown>,
	onError: (message: string) => void,
): Promise<void> {
	try {
		await action();
	} catch (error) {
		onError(error instanceof Error ? error.message : String(error));
	}
}
