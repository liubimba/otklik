import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Anchors the domain vocabulary for the letter-review sheet. The hh.ru
 * concept for sending an application is "Отклик" — the button labels used
 * to say "Отправить" / "Отправляем…", which the user flagged as visually
 * inconsistent with the surrounding status/toast text ("Отклик поставлен
 * в очередь", "Отклик отправлен", "Отправляем отклик…"). Unifying
 * everything under "Откликнуться" / "Откликаемся…" avoids the
 * "where's the send button" scan failure.
 */
const ruPath = path.resolve(__dirname, "../../messages/ru.json");
const ruMessages = JSON.parse(fs.readFileSync(ruPath, "utf-8")) as Record<
	string,
	string
>;

describe("i18n — letter-review action labels use the 'Отклик' vocabulary", () => {
	it("review_button_submit is 'Откликнуться'", () => {
		expect(ruMessages.review_button_submit).toBe("Откликнуться");
	});

	it("review_button_submitting is 'Откликаемся…'", () => {
		expect(ruMessages.review_button_submitting).toBe("Откликаемся…");
	});

	it("supporting status/toast text also uses 'Отклик'", () => {
		expect(ruMessages.review_sent_status).toBe("Отклик отправлен");
		expect(ruMessages.review_submit_success).toBe(
			"Отклик поставлен в очередь на отправку",
		);
		expect(ruMessages.review_sending_status).toBe("Отправляем отклик…");
	});
});
