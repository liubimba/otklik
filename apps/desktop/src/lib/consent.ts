import { shell } from "$lib/shell";

export const TERMS_VERSION = 1;

export interface Consent {
	termsVersion: number;
	consentGiven: boolean;
	acceptedAt: string;
}

export async function loadConsent(): Promise<Consent | null> {
	const text = await shell().consent.load();
	if (!text) {
		return null;
	}
	try {
		return JSON.parse(text) as Consent;
	} catch {
		return null;
	}
}

export async function saveConsent(isConsentGiven: boolean): Promise<void> {
	const consent: Consent = {
		acceptedAt: new Date().toISOString(),
		termsVersion: TERMS_VERSION,
		consentGiven: isConsentGiven,
	};
	await shell().consent.save(JSON.stringify(consent));
}

export function isValidConsent(consent: Consent | null): boolean {
	return (
		consent !== null &&
		consent.termsVersion >= TERMS_VERSION &&
		consent.consentGiven === true
	);
}
