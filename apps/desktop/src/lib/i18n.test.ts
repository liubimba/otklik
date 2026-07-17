import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

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
