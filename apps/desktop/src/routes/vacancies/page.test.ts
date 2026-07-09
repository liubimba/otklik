import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Capture the getters the page hands to createAllVacanciesQuery. Calling them
// after an interaction tells us exactly what the query would have requested,
// without standing up a QueryClient.
const stub = vi.hoisted(() => ({
	getStatuses: null as (() => readonly string[] | undefined) | null,
	getSearch: null as (() => string | undefined) | null,
	getLimit: null as (() => number) | null,
}));

vi.mock("$lib/queries", () => ({
	query: {
		all_vacancies: {
			create: (
				getStatuses: () => readonly string[] | undefined,
				getSearch: () => string | undefined,
				getLimit: () => number,
			) => {
				stub.getStatuses = getStatuses;
				stub.getSearch = getSearch;
				stub.getLimit = getLimit;
				return {
					data: { items: [], total: 0 },
					isPending: false,
					isError: false,
					isFetching: false,
					error: null,
				};
			},
		},
	},
}));

import VacanciesPage from "./+page.svelte";

const SEARCH_DEBOUNCE_MS = 300;

function searchBox(): HTMLInputElement {
	return screen.getByRole("searchbox");
}

describe("/vacancies — search box", () => {
	beforeEach(() => {
		stub.getSearch = null;
		vi.useFakeTimers();
	});

	it("feeds the typed text to the query after the debounce", async () => {
		const user = userEvent.setup({
			advanceTimers: vi.advanceTimersByTime.bind(vi),
		});
		render(VacanciesPage);

		await user.type(searchBox(), "python");
		await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);

		expect(stub.getSearch?.()).toBe("python");
	});

	it("does not fire a request per keystroke", async () => {
		const user = userEvent.setup({
			advanceTimers: vi.advanceTimersByTime.bind(vi),
		});
		render(VacanciesPage);

		await user.type(searchBox(), "go");
		// Still inside the debounce window — the query must not have moved yet.
		expect(stub.getSearch?.()).toBeFalsy();

		await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
		expect(stub.getSearch?.()).toBe("go");
	});

	it("clearing the box resets the query back to no search", async () => {
		const user = userEvent.setup({
			advanceTimers: vi.advanceTimersByTime.bind(vi),
		});
		render(VacanciesPage);

		await user.type(searchBox(), "rust");
		await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
		expect(stub.getSearch?.()).toBe("rust");

		await user.clear(searchBox());
		await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
		expect(stub.getSearch?.()).toBeFalsy();
	});
});
