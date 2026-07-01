import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryClient } from "@tanstack/svelte-query";

interface MutationConfig<T, V> {
	mutationFn: (vars: V) => Promise<T>;
	onSuccess?: (data: T, vars: V, ctx: unknown) => void | Promise<void>;
}

const capturedConfigs: MutationConfig<unknown, unknown>[] = [];

vi.mock("@tanstack/svelte-query", async () => {
	const actual = await vi.importActual<Record<string, unknown>>(
		"@tanstack/svelte-query",
	);
	return {
		...actual,
		createMutation: <T, V>(factory: () => MutationConfig<T, V>) => {
			const config = factory();
			capturedConfigs.push(config as MutationConfig<unknown, unknown>);
			return { mutateAsync: (vars: V) => config.mutationFn(vars) };
		},
	};
});

vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

vi.mock("$lib/api/client", () => ({
	API: {
		application: {
			submit: vi.fn(async () => ({ status: "letter_sending" })),
			save: vi.fn(async () => ({ text: "s", version: 1, created_at: "x" })),
			generate: vi.fn(async () => ({ text: "g" })),
			skip: vi.fn(async () => ({ status: "skipped" })),
			retry: vi.fn(async () => ({ status: "letter_pending" })),
		},
	},
}));

const { createVacanciesActions } = await import("./vacancies");
const { API } = await import("$lib/api/client");
const { applicationQueryKey } = await import("$lib/queries/applications");

function makeFakeClient() {
	return {
		setQueryData: vi.fn(),
		invalidateQueries: vi.fn(async () => {}),
	} as unknown as QueryClient;
}

beforeEach(() => {
	capturedConfigs.length = 0;
	vi.clearAllMocks();
});

afterEach(() => {
	vi.clearAllMocks();
});

describe("createVacanciesActions", () => {
	it("returns the full mutation surface: submit / save / generate / retry / skip", () => {
		const actions = createVacanciesActions(makeFakeClient(), 7);
		expect(Object.keys(actions).sort()).toEqual([
			"generate",
			"retry",
			"save",
			"skip",
			"submit",
		]);
	});

	it("submit forwards optional text via API.application.submit", async () => {
		const actions = createVacanciesActions(makeFakeClient(), 7);
		await actions.submit.mutateAsync({ text: "final" });
		expect(API.application.submit).toHaveBeenCalledWith(7, "final");
	});

	it("submit works with empty params (undefined text)", async () => {
		const actions = createVacanciesActions(makeFakeClient(), 7);
		await actions.submit.mutateAsync({});
		expect(API.application.submit).toHaveBeenCalledWith(7, undefined);
	});

	it("save forwards text via API.application.save", async () => {
		const actions = createVacanciesActions(makeFakeClient(), 11);
		await actions.save.mutateAsync({ text: "draft" });
		expect(API.application.save).toHaveBeenCalledWith(11, "draft");
	});

	it("generate invokes API.application.generate for the fixed vacancy id", async () => {
		const actions = createVacanciesActions(makeFakeClient(), 22);
		await actions.generate.mutateAsync();
		expect(API.application.generate).toHaveBeenCalledWith(22);
	});
});

describe("onSuccess side-effects", () => {
	it("submit.onSuccess writes ApplicationDetail into the cache via setQueryData", async () => {
		const client = makeFakeClient();
		createVacanciesActions(client, 42);
		// submit is registered first in vacancies.ts (order: submit, save,
		// generate, retry, skip).
		const submitCfg = capturedConfigs[0];
		const result = { status: "letter_sending" };
		await submitCfg.onSuccess?.(result, { text: "x" }, undefined);

		expect(vi.mocked(client.setQueryData)).toHaveBeenCalledWith(
			applicationQueryKey(42),
			result,
		);
	});

	it("save.onSuccess invalidates the application cache (fresh detail on next read)", async () => {
		const client = makeFakeClient();
		createVacanciesActions(client, 42);
		const saveCfg = capturedConfigs[1];
		await saveCfg.onSuccess?.({}, { text: "x" }, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(42),
		});
	});

	it("generate.onSuccess invalidates the application cache", async () => {
		const client = makeFakeClient();
		createVacanciesActions(client, 42);
		const generateCfg = capturedConfigs[2];
		await generateCfg.onSuccess?.({ text: "g" }, undefined, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(42),
		});
	});

	it("retry.onSuccess writes ApplicationDetail into the cache", async () => {
		const client = makeFakeClient();
		createVacanciesActions(client, 42);
		const retryCfg = capturedConfigs[3];
		const result = { status: "letter_pending" };
		await retryCfg.onSuccess?.(result, undefined, undefined);

		expect(vi.mocked(client.setQueryData)).toHaveBeenCalledWith(
			applicationQueryKey(42),
			result,
		);
	});

	it("skip.onSuccess writes ApplicationDetail into the cache", async () => {
		const client = makeFakeClient();
		createVacanciesActions(client, 42);
		const skipCfg = capturedConfigs[4];
		const result = { status: "skipped" };
		await skipCfg.onSuccess?.(result, undefined, undefined);

		expect(vi.mocked(client.setQueryData)).toHaveBeenCalledWith(
			applicationQueryKey(42),
			result,
		);
	});
});
