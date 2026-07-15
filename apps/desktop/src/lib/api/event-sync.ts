import { query } from "$lib/queries";
import { connection } from "$lib/stores/connection.svelte";
import { type QueryClient, notifyManager } from "@tanstack/svelte-query";
import type { ServerEvent } from "./types";

export interface EventSync {
	/** Одно WS-событие → мутации кэша (батчатся в одно уведомление). */
	onEvent: (event: ServerEvent) => void;
	/** Сокет (пере)подключился: бэкенд жив, ресинхронизируем то, что живёт на событиях. */
	onConnect: () => void;
	/** Сокет отвалился (и переподключается): бэкенд недоступен. */
	onDisconnect: () => void;
}

/**
 * Синхронизация клиентского кэша с WS-потоком бэкенда. Вынесена из корневого
 * layout, чтобы её можно было проверить без монтирования всего приложения.
 *
 * `lastSearchId` живёт в замыкании: он нужен, чтобы отличить старт нового поиска
 * (сменился id → область счётчика очереди сменилась) от тиков прогресса того же
 * поиска, на каждый из которых дёргать COUNT было бы расточительно.
 */
export function createEventSync(queryClient: QueryClient): EventSync {
	let lastSearchId: string | null = null;

	function onEvent(event: ServerEvent): void {
		// Без батча каждый подписчик перерисовывается по разу на КАЖДУЮ мутацию
		// (setQueryData + invalidateQueries). batch схлопывает их в одно
		// уведомление на событие — иначе список вакансий/лист письма трясёт
		// во время авто-сабмита.
		notifyManager.batch(() => {
			switch (event.type) {
				case "vacancy_new":
					query.vacancies.apply(queryClient, event);
					query.all_vacancies.invalidate(queryClient);
					// PARSED не считается «требует внимания», а переход, который
					// начнёт считаться, придёт своим application_event и
					// инвалидирует сводку ниже. Дёргать её здесь — лишний GET на
					// каждую спарсенную вакансию.
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
					// Архив рисует статус из полезной нагрузки списка, так что
					// сдвинуть его баджи может только перезагрузка списка.
					query.all_vacancies.invalidate(queryClient);
					query.summary.invalidate(queryClient);
			}
		});
	}

	function onConnect(): void {
		connection.online();
		// Каждый (пере)коннект — момент «могли пропустить события»: у бэкенда нет
		// буфера воспроизведения, всё опубликованное, пока мы лежали (или в гонке
		// до его старта), потеряно. Плюс auth: если приложение поднялось РАНЬШЕ
		// бэкенда, первый успешный коннект — это когда «вечный скелетон» профиля
		// наконец получает настоящий статус (запрос auth к тому моменту в ошибке
		// и сам не перезапросится).
		queryClient.invalidateQueries({ queryKey: query.auth.key });
		query.summary.invalidate(queryClient);
	}

	function onDisconnect(): void {
		connection.offline();
	}

	return { onEvent, onConnect, onDisconnect };
}
