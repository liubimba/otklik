import { QueryClient } from "@tanstack/svelte-query";
import { render, screen, waitFor } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listAll = vi.hoisted(() => vi.fn());

vi.mock("$lib/api/client", () => ({
	API: { vacancies: { listAll, get: vi.fn() } },
}));

import Harness from "./page-harness.svelte";

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return render(Harness, { props: { queryClient } });
}

describe("/vacancies — search reaches the API", () => {
	beforeEach(() => {
		listAll.mockReset();
		listAll.mockResolvedValue({ items: [], total: 0 });
	});

	it("requests the typed text", async () => {
		const user = userEvent.setup();
		renderPage();

		await waitFor(() => expect(listAll).toHaveBeenCalled());
		await user.type(screen.getByRole("searchbox"), "python");

		await waitFor(
			() => {
				const last = listAll.mock.calls.at(-1)?.[0];
				expect(last).toMatchObject({ search: "python" });
			},
			{ timeout: 2000 },
		);
	});

	it("requests the ticked chips as a union", async () => {
		const user = userEvent.setup();
		renderPage();

		await waitFor(() => expect(listAll).toHaveBeenCalled());
		await user.click(screen.getByRole("button", { name: "Готов к отклику" }));
		await user.click(screen.getByRole("button", { name: "Пропущено" }));

		await waitFor(() => {
			const last = listAll.mock.calls.at(-1)?.[0];
			expect(last?.statuses).toEqual(["letter_ready", "skipped"]);
		});
	});
});
