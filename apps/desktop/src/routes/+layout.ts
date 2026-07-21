import { API } from "$lib/api/client";
import { isValidConsent, loadConsent } from "$lib/consent";
import type { Consent } from "$lib/consent";
import { redirect } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";

export const ssr = false;
export const prerender = false;

const CONSENT_SCREEN = "/onboarding";
const BROWSER_SCREEN = "/onboarding/browser";

let consentGranted = false;
let chromiumReady = false;

export const load: LayoutLoad = async ({ url }) => {
	if (url.pathname === CONSENT_SCREEN) {
		return {};
	}
	if (!consentGranted) {
		const consent: Consent | null = await loadConsent();
		if (!isValidConsent(consent)) {
			redirect(307, CONSENT_SCREEN);
		}
		consentGranted = true;
	}
	if (url.pathname === BROWSER_SCREEN || chromiumReady) {
		return {};
	}
	try {
		const state = await API.setup.state();
		if (!state.chromium_installed) {
			redirect(307, BROWSER_SCREEN);
		}
		chromiumReady = true;
	} catch (error) {
		if (isRedirect(error)) throw error;
	}
	return {};
};

function isRedirect(error: unknown): boolean {
	return (
		typeof error === "object" &&
		error !== null &&
		"status" in error &&
		"location" in error
	);
}
