import { API } from "$lib/api/client";
import type { SecretStorage } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const secretStorageQueryKey = ["secret-storage"] as const;

export function createSecretStorageQuery() {
	return createQuery<SecretStorage>(() => ({
		queryKey: secretStorageQueryKey,
		queryFn: API.system.secretStorage,
		staleTime: Number.POSITIVE_INFINITY,
	}));
}
