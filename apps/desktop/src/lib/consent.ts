import {
	BaseDirectory,
	exists,
	mkdir,
	readTextFile,
	writeTextFile,
} from "@tauri-apps/plugin-fs";

export const TERMS_VERSION = 1;

export interface Consent {
	termsVersion: number;
	consentGiven: boolean;
	acceptedAt: string;
}

const CONSENT_DIR = ".headhunter_ai";
const CONSENT_FILE = `${CONSENT_DIR}/consent.json`;
const HOME = {
	baseDir: BaseDirectory.Home,
};

export async function loadConsent(): Promise<Consent | null> {
	if (!(await exists(CONSENT_FILE, HOME))) {
		return null;
	}

	try {
		const text = await readTextFile(CONSENT_FILE, HOME);
		return JSON.parse(text) as Consent;
	} catch (e) {
		return null;
	}
}

export async function saveConsent(isConsentGiven: boolean): Promise<void> {
	await mkdir(CONSENT_DIR, { ...HOME, recursive: true });
	const consent: Consent = {
		acceptedAt: new Date().toISOString(),
		termsVersion: TERMS_VERSION,
		consentGiven: isConsentGiven,
	};
	await writeTextFile(CONSENT_FILE, JSON.stringify(consent), HOME);
}

export function isValidConsent(consent: Consent | null): boolean {
	return (
		consent !== null &&
		consent.termsVersion >= TERMS_VERSION &&
		consent.consentGiven === true
	);
}
