import { beforeEach, describe, expect, it, vi } from "vitest";

const loadConsent = vi.fn();
const isValidConsent = vi.fn();
vi.mock("$lib/consent", () => ({
	loadConsent: () => loadConsent(),
	isValidConsent: (c: unknown) => isValidConsent(c),
}));

const setupState = vi.fn();
vi.mock("$lib/api/client", () => ({
	API: { setup: { state: () => setupState() } },
}));

import { load } from "./+layout";

type Loaded = { redirectedTo?: string };

async function loadFor(pathname: string): Promise<Loaded> {
	try {
		await (load as (e: { url: URL }) => Promise<unknown>)({
			url: new URL(`http://localhost${pathname}`),
		});
		return {};
	} catch (thrown) {
		const redirect = thrown as { status?: number; location?: string };
		if (redirect.location) return { redirectedTo: redirect.location };
		throw thrown;
	}
}

describe("layout load — куда пускать пользователя", () => {
	beforeEach(() => {
		loadConsent.mockReset();
		isValidConsent.mockReset();
		setupState.mockReset();
		isValidConsent.mockReturnValue(true);
		setupState.mockResolvedValue({ chromium_installed: true });
	});

	it("без согласия уводит на онбординг", async () => {
		isValidConsent.mockReturnValue(false);
		expect((await loadFor("/")).redirectedTo).toBe("/onboarding");
	});

	it("согласие есть, браузер есть — пускает в приложение", async () => {
		expect((await loadFor("/")).redirectedTo).toBeUndefined();
	});

	it("согласие есть, а браузера нет — уводит докачивать, а не в мёртвое приложение", async () => {
		setupState.mockResolvedValue({ chromium_installed: false });
		expect((await loadFor("/")).redirectedTo).toBe("/onboarding/browser");
	});

	it("сам экран онбординга не заворачивает — иначе цикл", async () => {
		isValidConsent.mockReturnValue(false);
		expect((await loadFor("/onboarding")).redirectedTo).toBeUndefined();
	});

	it("экран загрузки браузера не заворачивает сам на себя", async () => {
		setupState.mockResolvedValue({ chromium_installed: false });
		expect((await loadFor("/onboarding/browser")).redirectedTo).toBeUndefined();
	});

	it("недоступный бэкенд не запирает пользователя на онбординге", async () => {
		setupState.mockRejectedValue(new Error("backend is down"));
		expect((await loadFor("/")).redirectedTo).toBeUndefined();
	});
});
