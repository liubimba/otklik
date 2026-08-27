import { API } from "$lib/api/client";
import type { Settings } from "$lib/api/types";
import { settingsQueryKey } from "$lib/queries/settings";
import { settingsToWrite } from "$lib/schemas/settings";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createSettingsActions(queryClient: QueryClient) {
	return {
		updateUser: createMutation(() => ({
			mutationFn: async (params: { user: Partial<Settings["user"]> }) => {
				const current = queryClient.getQueryData<Settings>(settingsQueryKey);
				if (!current) {
					throw new Error("Settings not loaded");
				}
				const write = settingsToWrite(current);
				return API.settings.update({
					...write,
					user: { ...write.user, ...params.user },
				});
			},
			onSuccess(saved) {
				queryClient.setQueryData(settingsQueryKey, saved);
			},
		})),
	};
}
