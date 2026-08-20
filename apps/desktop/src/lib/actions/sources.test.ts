import type { QueryClient } from "@tanstack/svelte-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
		sources: {
			list: vi.fn(async () => []),
			create: vi.fn(async () => ({ id: 1 })),
			update: vi.fn(async () => ({ id: 1 })),
			remove: vi.fn(async () => undefined),
			refresh: vi.fn(async () => ({ id: 1 })),
			refreshAll: vi.fn(async () => ({ refreshed: 2 })),
		},
	},
}));

const { createSourcesActions } = await import("./sources");
const { API } = await import("$lib/api/client");
const { sourcesQueryKey } = await import("$lib/queries/sources");

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

describe("createSourcesActions", () => {
	it("returns the full mutation surface: add / update / remove / refresh / refreshAll", () => {
		const actions = createSourcesActions(makeFakeClient());
		expect(Object.keys(actions).sort()).toEqual([
			"add",
			"refresh",
			"refreshAll",
			"remove",
			"update",
		]);
	});

	it("add forwards body via API.sources.create", async () => {
		const actions = createSourcesActions(makeFakeClient());
		const body = {
			label: "Site",
			kind: "web" as const,
			url: "https://example.com",
		};
		await actions.add.mutateAsync(body);
		expect(API.sources.create).toHaveBeenCalledWith(body);
	});

	it("update forwards id and body via API.sources.update", async () => {
		const actions = createSourcesActions(makeFakeClient());
		const body = {
			label: "Repo",
			kind: "github" as const,
			url: "https://github.com/x",
		};
		await actions.update.mutateAsync({ id: 5, body });
		expect(API.sources.update).toHaveBeenCalledWith(5, body);
	});

	it("remove forwards id via API.sources.remove", async () => {
		const actions = createSourcesActions(makeFakeClient());
		await actions.remove.mutateAsync(9);
		expect(API.sources.remove).toHaveBeenCalledWith(9);
	});

	it("refresh forwards id via API.sources.refresh", async () => {
		const actions = createSourcesActions(makeFakeClient());
		await actions.refresh.mutateAsync(3);
		expect(API.sources.refresh).toHaveBeenCalledWith(3);
	});

	it("refreshAll invokes API.sources.refreshAll", async () => {
		const actions = createSourcesActions(makeFakeClient());
		await actions.refreshAll.mutateAsync();
		expect(API.sources.refreshAll).toHaveBeenCalled();
	});
});

describe("onSuccess side-effects", () => {
	it("add.onSuccess invalidates the sources cache", async () => {
		const client = makeFakeClient();
		createSourcesActions(client);
		const addCfg = capturedConfigs[0];
		await addCfg.onSuccess?.({ id: 1 }, undefined, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: sourcesQueryKey,
		});
	});

	it("update.onSuccess invalidates the sources cache", async () => {
		const client = makeFakeClient();
		createSourcesActions(client);
		const updateCfg = capturedConfigs[1];
		await updateCfg.onSuccess?.({ id: 1 }, undefined, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: sourcesQueryKey,
		});
	});

	it("remove.onSuccess invalidates the sources cache", async () => {
		const client = makeFakeClient();
		createSourcesActions(client);
		const removeCfg = capturedConfigs[2];
		await removeCfg.onSuccess?.(undefined, undefined, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: sourcesQueryKey,
		});
	});

	it("refresh.onSuccess invalidates the sources cache", async () => {
		const client = makeFakeClient();
		createSourcesActions(client);
		const refreshCfg = capturedConfigs[3];
		await refreshCfg.onSuccess?.({ id: 1 }, undefined, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: sourcesQueryKey,
		});
	});

	it("refreshAll.onSuccess invalidates the sources cache", async () => {
		const client = makeFakeClient();
		createSourcesActions(client);
		const refreshAllCfg = capturedConfigs[4];
		await refreshAllCfg.onSuccess?.({ refreshed: 2 }, undefined, undefined);

		expect(vi.mocked(client.invalidateQueries)).toHaveBeenCalledWith({
			queryKey: sourcesQueryKey,
		});
	});
});
