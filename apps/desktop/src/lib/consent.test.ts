import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	TERMS_VERSION,
	isValidConsent,
	loadConsent,
	saveConsent,
} from "./consent";

const load = vi.fn();
const save = vi.fn();

beforeEach(() => {
	load.mockReset();
	save.mockReset();
	vi.stubGlobal("otklik", { consent: { load, save } });
});

describe("loadConsent", () => {
	it("returns null when the bridge has no stored consent", async () => {
		load.mockResolvedValue(null);
		await expect(loadConsent()).resolves.toBeNull();
	});

	it("parses and returns the JSON payload the bridge provides", async () => {
		load.mockResolvedValue(
			JSON.stringify({
				termsVersion: TERMS_VERSION,
				consentGiven: true,
				acceptedAt: "2026-01-01T00:00:00.000Z",
			}),
		);
		expect(await loadConsent()).toEqual({
			termsVersion: TERMS_VERSION,
			consentGiven: true,
			acceptedAt: "2026-01-01T00:00:00.000Z",
		});
	});

	it("returns null when the stored text is not valid JSON", async () => {
		load.mockResolvedValue("not-json");
		await expect(loadConsent()).resolves.toBeNull();
	});
});

describe("saveConsent", () => {
	it("serializes a granted consent and writes it through the bridge", async () => {
		save.mockResolvedValue(undefined);
		await saveConsent(true);
		expect(save).toHaveBeenCalledTimes(1);
		const written = JSON.parse(save.mock.calls[0][0]);
		expect(written.consentGiven).toBe(true);
		expect(written.termsVersion).toBe(TERMS_VERSION);
	});
});

describe("isValidConsent", () => {
	it("accepts a current, granted consent", () => {
		expect(
			isValidConsent({
				termsVersion: TERMS_VERSION,
				consentGiven: true,
				acceptedAt: "x",
			}),
		).toBe(true);
	});

	it("rejects null, ungranted, or an outdated terms version", () => {
		expect(isValidConsent(null)).toBe(false);
		expect(
			isValidConsent({
				termsVersion: TERMS_VERSION,
				consentGiven: false,
				acceptedAt: "x",
			}),
		).toBe(false);
		expect(
			isValidConsent({ termsVersion: 0, consentGiven: true, acceptedAt: "x" }),
		).toBe(false);
	});
});
