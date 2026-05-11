import { isValidConsent, loadConsent } from "$lib/consent";
import type { Consent } from "$lib/consent";
// Tauri doesn't have a Node.js server to do proper SSR
// so we use adapter-static with a fallback to index.html to put the site in SPA mode
// See: https://svelte.dev/docs/kit/single-page-apps
// See: https://v2.tauri.app/start/frontend/sveltekit/ for more info
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
