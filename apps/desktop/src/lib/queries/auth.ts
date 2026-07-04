import { API } from "$lib/api/client";
import type { AuthEvent, AuthStatus } from "$lib/api/types";
import { type QueryClient, createQuery } from "@tanstack/svelte-query";

export const authQueryKey = ["auth"];

export function createAuthQuery() {
	return createQuery<AuthStatus>(() => ({
		queryKey: authQueryKey,
		queryFn: () => API.auth.status(),
		staleTime: 30_000,
	}));
}

export function applyAuthEvent(queryClient: QueryClient, event: AuthEvent) {
	queryClient.setQueryData(authQueryKey, event.data);
}
