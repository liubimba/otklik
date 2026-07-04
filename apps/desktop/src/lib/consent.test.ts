import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * @tauri-apps/plugin-fs calls window.__TAURI_INTERNALS__ at import time. Stub
 * every export we touch so consent.ts can run in Node.
 */
const fsMock = vi.hoisted(() => ({
	exists: vi.fn(),
	mkdir: vi.fn(),
	readTextFile: vi.fn(),
	writeTextFile: vi.fn(),
	BaseDirectory: { Home: "home" as const },
}));

vi.mock("@tauri-apps/plugin-fs", () => fsMock);

const { TERMS_VERSION, isValidConsent, loadConsent, saveConsent } =
	await import("./consent");

beforeEach(() => {
	fsMock.exists.mockReset();
	fsMock.mkdir.mockReset();
	fsMock.readTextFile.mockReset();
	fsMock.writeTextFile.mockReset();
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("loadConsent", () => {
	it("returns null when the consent file does not exist", async () => {
		fsMock.exists.mockResolvedValue(false);
		await expect(loadConsent()).resolves.toBeNull();
		expect(fsMock.readTextFile).not.toHaveBeenCalled();
	});

	it("parses and returns the JSON payload when the file exists", async () => {
		fsMock.exists.mockResolvedValue(true);
		fsMock.readTextFile.mockResolvedValue(
			JSON.stringify({
				termsVersion: TERMS_VERSION,
				consentGiven: true,
				acceptedAt: "2026-01-01T00:00:00.000Z",
			}),
		);

		const consent = await loadConsent();
		expect(consent).toEqual({
			termsVersion: TERMS_VERSION,
			consentGiven: true,
			acceptedAt: "2026-01-01T00:00:00.000Z",
		});
	});

	it("returns null when the file exists but contains invalid JSON", async () => {
		fsMock.exists.mockResolvedValue(true);
		fsMock.readTextFile.mockResolvedValue("not-json");

		await expect(loadConsent()).resolves.toBeNull();
	});

	it("returns null on any readTextFile error", async () => {
		fsMock.exists.mockResolvedValue(true);
		fsMock.readTextFile.mockRejectedValue(new Error("EACCES"));

		await expect(loadConsent()).resolves.toBeNull();
	});
});

describe("saveConsent", () => {
	it("creates the parent dir (recursive) and writes the consent JSON", async () => {
		fsMock.mkdir.mockResolvedValue(undefined);
		fsMock.writeTextFile.mockResolvedValue(undefined);

		await saveConsent(true);

		expect(fsMock.mkdir).toHaveBeenCalledWith(
			".headhunter_ai",
			expect.objectContaining({ recursive: true }),
		);
		expect(fsMock.writeTextFile).toHaveBeenCalledWith(
			".headhunter_ai/consent.json",
			expect.stringContaining('"consentGiven":true'),
			expect.any(Object),
		);
	});

	it("propagates the isConsentGiven flag verbatim", async () => {
		fsMock.mkdir.mockResolvedValue(undefined);
		fsMock.writeTextFile.mockResolvedValue(undefined);

		await saveConsent(false);
		const [, payload] = fsMock.writeTextFile.mock.calls[0];
		const parsed = JSON.parse(payload as string);
		expect(parsed.consentGiven).toBe(false);
		expect(parsed.termsVersion).toBe(TERMS_VERSION);
		// acceptedAt is a valid ISO string
		expect(() =>
			new Date(parsed.acceptedAt as string).toISOString(),
		).not.toThrow();
	});
});

describe("isValidConsent", () => {
	it("rejects null", () => {
		expect(isValidConsent(null)).toBe(false);
	});

	it("rejects consent that was not given", () => {
		expect(
			isValidConsent({
				termsVersion: TERMS_VERSION,
				consentGiven: false,
				acceptedAt: "x",
			}),
		).toBe(false);
	});

	it("rejects consent for an older terms version", () => {
		expect(
			isValidConsent({
				termsVersion: TERMS_VERSION - 1,
				consentGiven: true,
				acceptedAt: "x",
			}),
		).toBe(false);
	});

	it("accepts consent for the current terms version", () => {
		expect(
			isValidConsent({
				termsVersion: TERMS_VERSION,
				consentGiven: true,
				acceptedAt: "x",
			}),
		).toBe(true);
	});

	it("accepts consent from a future terms version (forward-compat)", () => {
		expect(
			isValidConsent({
				termsVersion: TERMS_VERSION + 1,
				consentGiven: true,
				acceptedAt: "x",
			}),
		).toBe(true);
	});
});
