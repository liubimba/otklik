import type { QueryClient } from "@tanstack/svelte-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * `createMutation` is Svelte-context bound (it opens a `Query` subscription
 * against the QueryClient stored in Svelte context). We intercept it at the
 * module boundary and record every config the action factory hands it — the
 * meaningful surface of an action file *is* those configs (mutationFn +
 * onSuccess). Nothing to test in the createMutation return value itself.
 */

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
			return {
				mutateAsync: (vars: V) => config.mutationFn(vars),
			};
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

// API mocks — each mutationFn calls into $lib/api/client, so stub the
// endpoints we care about.
vi.mock("$lib/api/client", () => ({
	API: {
		application: {
			generate: vi.fn(async (_id: number) => ({ text: "generated" })),
			save: vi.fn(async (_id: number, _text: string) => ({
				text: "saved",
				version: 2,
				created_at: "x",
			})),
			submit: vi.fn(async (_id: number, _text?: string) => ({
				status: "letter_sending",
			})),
			skip: vi.fn(async (_id: number) => ({ status: "skipped" })),
			retry: vi.fn(async (_id: number) => ({ status: "letter_pending" })),
		},
	},
}));

const { createLetterReviewActions } = await import("./letter-review");
const { API } = await import("$lib/api/client");
const { applicationQueryKey, coverLettersHistoryQueryKey } = await import(
	"$lib/queries/applications"
);

function makeFakeClient() {
	return {
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

describe("createLetterReviewActions — mutation shapes", () => {
	it("exposes generate / save / submit / skip / retry", () => {
		const client = makeFakeClient();
		const actions = createLetterReviewActions(client);
		expect(Object.keys(actions).sort()).toEqual([
			"generate",
			"retry",
			"save",
			"skip",
			"submit",
		]);
		expect(capturedConfigs).toHaveLength(5);
	});
});

describe("Mutation → API call bindings", () => {
	it("generate.mutateAsync(vacancyId) calls API.application.generate", async () => {
		const actions = createLetterReviewActions(makeFakeClient());
		await actions.generate.mutateAsync(7);
		expect(API.application.generate).toHaveBeenCalledWith(7);
	});

	it("save.mutateAsync({vacancyId, text}) forwards both to API.application.save", async () => {
		const actions = createLetterReviewActions(makeFakeClient());
		await actions.save.mutateAsync({ vacancyId: 3, text: "draft" });
		expect(API.application.save).toHaveBeenCalledWith(3, "draft");
	});

	it("submit.mutateAsync forwards text when provided (dirty-submit)", async () => {
		const actions = createLetterReviewActions(makeFakeClient());
		await actions.submit.mutateAsync({ vacancyId: 5, text: "final" });
		expect(API.application.submit).toHaveBeenCalledWith(5, "final");
	});

	it("submit.mutateAsync passes undefined text when omitted", async () => {
		const actions = createLetterReviewActions(makeFakeClient());
		await actions.submit.mutateAsync({ vacancyId: 5 });
		expect(API.application.submit).toHaveBeenCalledWith(5, undefined);
	});

	it("skip.mutateAsync(vacancyId) calls API.application.skip", async () => {
		const actions = createLetterReviewActions(makeFakeClient());
		await actions.skip.mutateAsync(9);
		expect(API.application.skip).toHaveBeenCalledWith(9);
	});

	it("retry.mutateAsync(vacancyId) calls API.application.retry", async () => {
		const actions = createLetterReviewActions(makeFakeClient());
		await actions.retry.mutateAsync(9);
		expect(API.application.retry).toHaveBeenCalledWith(9);
	});
});

describe("onSuccess invalidates the application + history caches", () => {
	async function runOnSuccessOf(
		configIndex: number,
		vars: unknown,
		result: unknown,
	): Promise<QueryClient> {
		const client = makeFakeClient();
		createLetterReviewActions(client);
		const config = capturedConfigs[configIndex];
		await config.onSuccess?.(result, vars, undefined);
		return client;
	}

	it("generate → invalidates the two caches for the vacancy", async () => {
		const client = await runOnSuccessOf(0, 42, { text: "g" });
		const invalidate = vi.mocked(client.invalidateQueries);
		expect(invalidate).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(42),
		});
		expect(invalidate).toHaveBeenCalledWith({
			queryKey: coverLettersHistoryQueryKey(42),
		});
	});

	it("save → invalidates using params.vacancyId (not the whole params object)", async () => {
		// save is the second config registered (generate=0, save=1).
		const client = await runOnSuccessOf(1, { vacancyId: 3, text: "x" }, {});
		const invalidate = vi.mocked(client.invalidateQueries);
		expect(invalidate).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(3),
		});
	});

	it("submit → invalidates using params.vacancyId", async () => {
		const client = await runOnSuccessOf(2, { vacancyId: 5, text: "y" }, {});
		const invalidate = vi.mocked(client.invalidateQueries);
		expect(invalidate).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(5),
		});
	});

	it("skip → invalidates using the raw vacancyId", async () => {
		const client = await runOnSuccessOf(3, 9, {});
		const invalidate = vi.mocked(client.invalidateQueries);
		expect(invalidate).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(9),
		});
	});

	it("retry → invalidates using the raw vacancyId", async () => {
		const client = await runOnSuccessOf(4, 9, {});
		const invalidate = vi.mocked(client.invalidateQueries);
		expect(invalidate).toHaveBeenCalledWith({
			queryKey: applicationQueryKey(9),
		});
	});
});
