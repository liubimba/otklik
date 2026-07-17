import { isValidConsent, loadConsent } from "$lib/consent";
import type { Consent } from "$lib/consent";
import { redirect } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";

export const ssr = false;
export const prerender = false;

export const load: LayoutLoad = async ({ url }) => {
	if (url.pathname === "/onboarding") {
		return {};
	}
	const consent: Consent | null = await loadConsent();
	if (!isValidConsent(consent)) {
		redirect(307, "/onboarding");
	}
	return {};
};
