import { m } from "$lib/paraglide/messages";

/**
 * До Task 2 перед каждой генерацией письма приложение пинговало модель, и
 * при мёртвой модели пользователь видел общее «ai layer is not ready».
 * Пинг убрали — он удваивал стоимость генерации (+59с на локальной модели).
 * Теперь наружу выходит сырой текст ошибки провайдера (`connection refused`,
 * `401 invalid api key`, `timeout`) — точнее, но нечитаемо для пользователя.
 *
 * Три частых случая переводим в понятную подсказку с следующим шагом.
 * Всё остальное показываем как есть — лучше сырой текст, чем ложная
 * уверенность за общей фразой.
 */
const HINTS: ReadonlyArray<[RegExp, () => string]> = [
	[
		/connection refused|ECONNREFUSED|Failed to connect/i,
		m.error_model_unreachable,
	],
	[/401|403|api key|unauthorized/i, m.error_model_bad_key],
	[/timeout|timed out/i, m.error_model_timeout],
];

export function explainProviderError(message: string): string {
	for (const [pattern, text] of HINTS) {
		if (pattern.test(message)) return text();
	}
	return message;
}
