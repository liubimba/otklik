import { API } from "$lib/api/client";
import { isValidConsent, loadConsent } from "$lib/consent";
import type { Consent } from "$lib/consent";
import { redirect } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";

export const ssr = false;
export const prerender = false;

const CONSENT_SCREEN = "/onboarding";
const BROWSER_SCREEN = "/onboarding/browser";

export const load: LayoutLoad = async ({ url }) => {
	if (url.pathname === CONSENT_SCREEN) {
		return {};
	}
	const consent: Consent | null = await loadConsent();
	if (!isValidConsent(consent)) {
		redirect(307, CONSENT_SCREEN);
	}
	if (url.pathname === BROWSER_SCREEN) {
		return {};
	}
	try {
		const state = await API.setup.state();
		if (!state.chromium_installed) {
			redirect(307, BROWSER_SCREEN);
		}
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
