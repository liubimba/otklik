import type { NotificationsSettings, ServerEvent } from "$lib/api/types";
import * as m from "$lib/paraglide/messages";

export type NotificationType =
	| "vacancy_parsed"
	| "letter_generated"
	| "letter_generated_sandbox"
	| "application_sent"
	| "error"
	| "captcha"
	| "auth_required"
	| "search_finished"
	| "rate_limited";

const TERMINAL_SEARCH = new Set([
	"exited",
	"canceled",
	"failed",
	"interrupted",
]);

export function eventNotificationType(
	event: ServerEvent,
): NotificationType | null {
	switch (event.type) {
		case "vacancy_new":
			return "vacancy_parsed";
		case "application_event":
			switch (event.data.status) {
				case "letter_ready":
					return "letter_generated";
				case "letter_sent":
					return "application_sent";
				case "error":
					return "error";
				default:
					return null;
			}
		case "captcha_event":
			return "captcha";
		case "auth_changed":
			return event.data.status === "unauthorized" ? "auth_required" : null;
		case "search_event":
			return TERMINAL_SEARCH.has(event.data.status) ? "search_finished" : null;
		case "rate_limit_event":
			return "rate_limited";
		default:
			return null;
	}
}

export function shouldNotify(
	type: NotificationType,
	settings: NotificationsSettings,
): boolean {
	return settings.enabled && settings[type];
}

export type NotificationSpec = { title: string; body: string; tag: string };

export function renderNotification(
	type: NotificationType,
	event?: ServerEvent,
): NotificationSpec {
	switch (type) {
		case "vacancy_parsed":
			return {
				title: m.notif_vacancy_parsed_title(),
				body: event?.type === "vacancy_new" ? event.data.title : "",
				tag: type,
			};
		case "letter_generated":
			return {
				title: m.notif_letter_generated_title(),
				body: m.notif_letter_generated_body(),
				tag: type,
			};
		case "letter_generated_sandbox":
			return {
				title: m.notif_letter_generated_sandbox_title(),
				body: m.notif_letter_generated_sandbox_body(),
				tag: type,
			};
		case "application_sent":
			return {
				title: m.notif_application_sent_title(),
				body: m.notif_application_sent_body(),
				tag: type,
			};
		case "error":
			return {
				title: m.notif_error_title(),
				body:
					event?.type === "application_event" && event.data.reason
						? event.data.reason
						: m.notif_error_body(),
				tag: type,
			};
		case "captcha":
			return {
				title: m.notif_captcha_title(),
				body: m.notif_captcha_body(),
				tag: type,
			};
		case "auth_required":
			return {
				title: m.notif_auth_required_title(),
				body: m.notif_auth_required_body(),
				tag: type,
			};
		case "search_finished":
			return {
				title: m.notif_search_finished_title(),
				body: m.notif_search_finished_body(),
				tag: type,
			};
		case "rate_limited":
			return {
				title: m.notif_rate_limited_title(),
				body: m.notif_rate_limited_body(),
				tag: type,
			};
	}
}

let permissionRequested = false;

export function showNotification(spec: NotificationSpec): void {
	if (typeof Notification === "undefined") {
		return;
	}
	const fire = () => {
		new Notification(spec.title, { body: spec.body, tag: spec.tag });
	};
	if (Notification.permission === "granted") {
		fire();
		return;
	}
	if (Notification.permission === "default" && !permissionRequested) {
		permissionRequested = true;
		void Notification.requestPermission().then((permission) => {
			if (permission === "granted") {
				fire();
			}
		});
	}
}

export function dispatchEventNotification(
	event: ServerEvent,
	settings: NotificationsSettings,
): void {
	const type = eventNotificationType(event);
	if (type === null || !shouldNotify(type, settings)) {
		return;
	}
	showNotification(renderNotification(type, event));
}

export function notifySandboxLetter(settings: NotificationsSettings): void {
	if (!shouldNotify("letter_generated_sandbox", settings)) {
		return;
	}
	showNotification(renderNotification("letter_generated_sandbox"));
}
