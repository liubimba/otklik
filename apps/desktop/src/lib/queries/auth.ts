import { API } from "$lib/api/client";
import type { AuthEvent, AuthStatus } from "$lib/api/types";
import type { BoardKind } from "$lib/boards";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const authQueryKey = ["auth"];

export function createAuthQuery(getBoard?: () => BoardKind | undefined) {
	return createQuery<AuthStatus>(() => {
		const board = getBoard?.();
		return {
			queryKey: [...authQueryKey, board ?? null],
			queryFn: () => API.auth.status(board),
			staleTime: 30_000,
		};
	});
}

export function applyAuthEvent(queryClient: QueryClient, _event: AuthEvent) {
	queryClient.invalidateQueries({ queryKey: authQueryKey });
}
