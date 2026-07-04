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

const generateMock = vi.fn(async () => ({
	text: "generated",
	model_used: "test",
	prompt_tokens: 0,
	completion_tokens: 0,
	total_tokens: 0,
	was_fallback: false,
	cost_usd: null,
}));

vi.mock("$lib/api/client", () => ({
	API: { application: { generate: generateMock } },
}));

const { createAICoverLetterActions } = await import("./ai");

const fakeClient = { invalidateQueries: vi.fn() } as unknown as QueryClient;

beforeEach(() => {
	capturedConfigs.length = 0;
	generateMock.mockClear();
});

afterEach(() => {
	vi.clearAllMocks();
});

describe("createAICoverLetterActions", () => {
	it("registers a single generate mutation", () => {
		const actions = createAICoverLetterActions(fakeClient, 1);
		expect(Object.keys(actions)).toEqual(["generate"]);
		expect(capturedConfigs).toHaveLength(1);
	});

	it("generate.mutateAsync() invokes API.application.generate with the fixed vacancy id", async () => {
		const actions = createAICoverLetterActions(fakeClient, 42);
		await actions.generate.mutateAsync();
		expect(generateMock).toHaveBeenCalledWith(42);
	});

	it("each call constructs a fresh mutation bound to its own vacancy id", async () => {
		const a = createAICoverLetterActions(fakeClient, 1);
		const b = createAICoverLetterActions(fakeClient, 2);
		await a.generate.mutateAsync();
		await b.generate.mutateAsync();
		const args = generateMock.mock.calls.map(
			(call: unknown[]) => call[0] as number,
		);
		expect(args).toEqual([1, 2]);
	});
});
