import type { AuthStatus } from "$lib/api/types";

/** Что показывает ячейка профиля. `offline` — новое: бэкенд недоступен. */
export type CellStatus =
	| "loading"
	| "unauthorized"
	| "authorizing"
	| "authorized"
	| "offline";

/**
 * Статус ячейки профиля из связности + ответа auth.
 *
 * Офлайн бьёт всё: пока бэкенд недоступен, показывать «Подключён» (по
 * протухшим данным) или крутить скелетон нельзя — ячейка честно говорит «нет
 * связи». Это же чинит «вечный скелетон» из бага №1: раньше отсутствие данных
 * (запрос auth в ошибке, потому что бэкенд лежал) трактовалось как «ещё
 * грузится» навсегда.
 *
 * Онлайн: есть данные — переносим статус (`unknown` от бэкенда читаем как «не
 * подключён», как и раньше); нет данных — короткий скелетон первой загрузки.
 */
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

/**
 * Число для баджа вкладки. Пока офлайн — `null` (бадж не рисуется): последний
 * успешный счётчик протух, и показывать его как живой — врать, что есть
 * вакансии (баг №2).
 */
export function badgeCount(
	isOffline: boolean,
	count: number | null,
): number | null {
	return isOffline ? null : count;
}

/**
 * Обёртка над действием авторизации, которое ходит в бэкенд. Раньше клик по
 * профилю при лежащем бэкенде падал молча — «ничего не происходит» (баг №2).
 * Теперь провал доходит до `onError` (тост), а не в пустоту.
 */
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
