const SPLASH_ID = "app-splash";
const FADE_MS = 260;

export function hideAppSplash(): void {
	const splash = document.getElementById(SPLASH_ID);
	if (!splash) return;
	splash.classList.add("is-hidden");
	setTimeout(() => splash.remove(), FADE_MS);
}
