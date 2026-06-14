import { getSettings } from "$lib/api/client";
import type { Settings } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const settingsQueryKey = ["settings"] as const;

export function createSettingsQuery() {
	return createQuery<Settings>(() => ({
		queryKey: settingsQueryKey,
		queryFn: getSettings,
		staleTime: Number.POSITIVE_INFINITY,
	}));
}
