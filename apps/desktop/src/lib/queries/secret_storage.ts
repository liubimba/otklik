import { API } from "$lib/api/client";
import type { SecretStorage } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const secretStorageQueryKey = ["secret-storage"] as const;

/**
 * Бэкенд решает режим хранения ключей (keychain vs файл) один раз при
 * старте и не меняет его на лету — staleTime: Infinity, без ручной
 * инвалидации.
 */
export function createSecretStorageQuery() {
	return createQuery<SecretStorage>(() => ({
		queryKey: secretStorageQueryKey,
		queryFn: API.system.secretStorage,
		staleTime: Number.POSITIVE_INFINITY,
	}));
}
