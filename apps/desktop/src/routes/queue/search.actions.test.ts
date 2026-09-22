import type { QueryClient } from "@tanstack/svelte-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

interface MutationConfig<T, V> {
	mutationFn: (vars: V) => Promise<T>;
	onSuccess?: (data: T, vars: V, ctx: unknown) => void | Promise<void>;
}

const captured: MutationConfig<unknown, unknown>[] = [];

vi.mock("@tanstack/svelte-query", async () => {
	const actual = await vi.importActual<Record<string, unknown>>(
		"@tanstack/svelte-query",
	);
	return {
		...actual,
		createMutation: <T, V>(factory: () => MutationConfig<T, V>) => {
			const config = factory();
			captured.push(config as MutationConfig<unknown, unknown>);
			return { mutateAsync: (vars: V) => config.mutationFn(vars) };
		},
	};
});

vi.mock("$lib/api/client", () => ({
	API: {
		search: {
			parse: {
				start: vi.fn(),
				cancel: vi.fn(),
				pause: vi.fn(),
				resume: vi.fn(),
			},
			filter: { open: vi.fn(), cancel: vi.fn(), confirm: vi.fn() },
		},
		auth: { signIn: vi.fn(), signInCancel: vi.fn(), signOut: vi.fn() },
	},
}));

vi.mock("$lib/stores/board.svelte", () => ({
	boardStore: { active: "hh_ru" },
}));

const { createSearchVacanciesActions } = await import(
	"./search.actions.svelte"
);
const { allVacanciesQueryKey } = await import("$lib/queries/all_vacancies");

const client = {
	setQueryData: vi.fn(),
	invalidateQueries: vi.fn(),
} as unknown as QueryClient;

beforeEach(() => {
	captured.length = 0;
	vi.mocked(client.invalidateQueries).mockClear();
	vi.mocked(client.setQueryData).mockClear();
});

describe("starting a new search", () => {
	it("re-scopes the queue by invalidating all-vacancies", async () => {
		createSearchVacanciesActions(client);
		const start = captured[0];

		await start.onSuccess?.(
			{
				search_id: "s1",
				board: "hh_ru",
				status: "running",
				parsed_pages: 0,
				parsed_vacancies: 0,
			},
			{},
			undefined,
		);

		const keys = vi
			.mocked(client.invalidateQueries)
			.mock.calls.map((c) => JSON.stringify(c[0]?.queryKey));
		expect(keys).toContain(JSON.stringify(allVacanciesQueryKey));
	});
});
