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

type Loaded = { redirectedTo?: string };
type LoadFor = (pathname: string) => Promise<Loaded>;

async function freshSession(): Promise<LoadFor> {
	vi.resetModules();
	const mod = await import("./+layout");
	const load = mod.load as (e: { url: URL }) => Promise<unknown>;
	return async (pathname: string) => {
		try {
			await load({ url: new URL(`http://localhost${pathname}`) });
			return {};
		} catch (thrown) {
			const redirect = thrown as { status?: number; location?: string };
			if (redirect.location) return { redirectedTo: redirect.location };
			throw thrown;
		}
	};
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
		const loadFor = await freshSession();
		isValidConsent.mockReturnValue(false);
		expect((await loadFor("/")).redirectedTo).toBe("/onboarding");
	});

	it("согласие есть, браузер есть — пускает в приложение", async () => {
		const loadFor = await freshSession();
		expect((await loadFor("/")).redirectedTo).toBeUndefined();
	});

	it("согласие есть, а браузера нет — уводит докачивать, а не в мёртвое приложение", async () => {
		const loadFor = await freshSession();
		setupState.mockResolvedValue({ chromium_installed: false });
		expect((await loadFor("/")).redirectedTo).toBe("/onboarding/browser");
	});

	it("сам экран онбординга не заворачивает — иначе цикл", async () => {
		const loadFor = await freshSession();
		isValidConsent.mockReturnValue(false);
		expect((await loadFor("/onboarding")).redirectedTo).toBeUndefined();
	});

	it("экран загрузки браузера не заворачивает сам на себя", async () => {
		const loadFor = await freshSession();
		setupState.mockResolvedValue({ chromium_installed: false });
		expect((await loadFor("/onboarding/browser")).redirectedTo).toBeUndefined();
	});

	it("недоступный бэкенд не запирает пользователя на онбординге", async () => {
		const loadFor = await freshSession();
		setupState.mockRejectedValue(new Error("backend is down"));
		expect((await loadFor("/")).redirectedTo).toBeUndefined();
	});
});

describe("layout load — цена смены вкладки", () => {
	beforeEach(() => {
		loadConsent.mockReset();
		isValidConsent.mockReset();
		setupState.mockReset();
		isValidConsent.mockReturnValue(true);
		setupState.mockResolvedValue({ chromium_installed: true });
	});

	it("не ходит в бэкенд на каждой смене вкладки", async () => {
		const loadFor = await freshSession();

		await loadFor("/queue");
		await loadFor("/vacancies");
		await loadFor("/history");

		expect(setupState).toHaveBeenCalledTimes(1);
	});

	it("не перечитывает файл согласия на каждой смене вкладки", async () => {
		const loadFor = await freshSession();

		await loadFor("/queue");
		await loadFor("/vacancies");
		await loadFor("/history");

		expect(loadConsent).toHaveBeenCalledTimes(1);
	});

	it("продолжает спрашивать, пока Chromium не установлен", async () => {
		const loadFor = await freshSession();
		setupState.mockResolvedValue({ chromium_installed: false });

		await loadFor("/queue");
		await loadFor("/queue");

		expect(setupState).toHaveBeenCalledTimes(2);
	});

	it("продолжает спрашивать, пока согласия нет", async () => {
		const loadFor = await freshSession();
		isValidConsent.mockReturnValue(false);

		await loadFor("/queue");
		await loadFor("/queue");

		expect(loadConsent).toHaveBeenCalledTimes(2);
	});

	it("не запоминает провал бэкенда — следующий переход спросит снова", async () => {
		const loadFor = await freshSession();
		setupState.mockRejectedValue(new Error("backend is down"));

		await loadFor("/queue");
		await loadFor("/queue");

		expect(setupState).toHaveBeenCalledTimes(2);
	});
});
