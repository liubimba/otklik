import { dispatchEventNotification } from "$lib/notifications/notifier";
import { query } from "$lib/queries";
import { connection } from "$lib/stores/connection.svelte";
import { type QueryClient, notifyManager } from "@tanstack/svelte-query";
import type { ServerEvent, Settings } from "./types";

export interface EventSync {
	onEvent: (event: ServerEvent) => void;
	onConnect: () => void;
	onDisconnect: () => void;
	onFatal: (detail?: string) => void;
}

export function createEventSync(queryClient: QueryClient): EventSync {
	let lastSearchId: string | null = null;

	function onEvent(event: ServerEvent): void {
		notifyManager.batch(() => {
			switch (event.type) {
				case "vacancy_new":
					query.vacancies.apply(queryClient, event);
					query.all_vacancies.invalidate(queryClient);
					break;
				case "search_event":
					query.search.vacancies.apply(queryClient, event);
					query.search.history.apply(queryClient, event);
					if (event.data.search_id !== lastSearchId) {
						lastSearchId = event.data.search_id;
						query.summary.invalidate(queryClient);
					}
					break;
				case "auth_changed":
					query.auth.apply(queryClient, event);
					break;
				case "application_event":
					query.application.apply(queryClient, event);
					query.all_vacancies.invalidate(queryClient);
					query.summary.invalidate(queryClient);
			}
		});

		const settings = queryClient.getQueryData<Settings>(query.settings.key);
		if (settings) {
			dispatchEventNotification(event, settings.notifications);
		}
	}

	function onConnect(): void {
		connection.online();
		queryClient.invalidateQueries({ queryKey: query.auth.key });
		query.summary.invalidate(queryClient);
	}

	function onDisconnect(): void {
		if (connection.isFailed) {
			return;
		}
		connection.offline();
	}

	function onFatal(detail?: string): void {
		connection.failed(detail);
	}

	return { onEvent, onConnect, onDisconnect, onFatal };
}
