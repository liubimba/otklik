import type { NotificationsSettings, ServerEvent } from "$lib/api/types";
import { describe, expect, it } from "vitest";
import { eventNotificationType, shouldNotify } from "./notifier";

const ALL_ON: NotificationsSettings = {
	enabled: true,
	vacancy_parsed: true,
	letter_generated: true,
	letter_generated_sandbox: true,
	application_sent: true,
	error: true,
	captcha: true,
	auth_required: true,
	search_finished: true,
	rate_limited: true,
};

describe("eventNotificationType", () => {
	it("maps a new vacancy", () => {
		expect(
			eventNotificationType({
				type: "vacancy_new",
				data: { title: "t" } as never,
				search_id: null,
			}),
		).toBe("vacancy_parsed");
	});

	it("maps application statuses to generation/sent/error", () => {
		const make = (status: string): ServerEvent => ({
			type: "application_event",
			data: {
				vacancy_id: 1,
				application_id: 1,
				status,
				reason: null,
				error_domain: null,
			} as never,
		});
		expect(eventNotificationType(make("letter_ready"))).toBe(
			"letter_generated",
		);
		expect(eventNotificationType(make("letter_sent"))).toBe("application_sent");
		expect(eventNotificationType(make("error"))).toBe("error");
		expect(eventNotificationType(make("letter_sending"))).toBeNull();
	});

	it("maps captcha and rate-limit events", () => {
		expect(
			eventNotificationType({
				type: "captcha_event",
				data: { vacancy_id: 1, application_id: 1 },
			}),
		).toBe("captcha");
		expect(
			eventNotificationType({
				type: "rate_limit_event",
				data: { reason: null },
			}),
		).toBe("rate_limited");
	});

	it("notifies about auth only when unauthorized", () => {
		expect(
			eventNotificationType({
				type: "auth_changed",
				data: { status: "unauthorized" },
			}),
		).toBe("auth_required");
		expect(
			eventNotificationType({
				type: "auth_changed",
				data: { status: "authorized" },
			}),
		).toBeNull();
	});

	it("notifies about search only on a terminal status", () => {
		const make = (status: string): ServerEvent => ({
			type: "search_event",
			data: {
				search_id: "s",
				parsed_vacancies: 0,
				parsed_pages: 0,
				status,
			} as never,
		});
		expect(eventNotificationType(make("exited"))).toBe("search_finished");
		expect(eventNotificationType(make("failed"))).toBe("search_finished");
		expect(eventNotificationType(make("running"))).toBeNull();
	});
});

describe("shouldNotify", () => {
	it("gates on the master toggle", () => {
		expect(shouldNotify("captcha", ALL_ON)).toBe(true);
		expect(shouldNotify("captcha", { ...ALL_ON, enabled: false })).toBe(false);
	});

	it("gates on the per-type toggle", () => {
		expect(shouldNotify("captcha", { ...ALL_ON, captcha: false })).toBe(false);
		expect(shouldNotify("error", { ...ALL_ON, error: false })).toBe(false);
	});
});
