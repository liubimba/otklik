import type { ContextSource } from "$lib/api/types";
import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const stub = vi.hoisted(() => ({
	sourcesQuery: vi.fn(),
	mutations: {
		add: { mutate: vi.fn() },
		remove: { mutate: vi.fn() },
		refresh: { mutate: vi.fn() },
		refreshAll: { mutate: vi.fn() },
	},
}));

vi.mock("$lib/queries", () => ({
	query: {
		sources: {
			create: stub.sourcesQuery,
		},
	},
}));

vi.mock("$lib/actions", () => ({
	createActions: () => ({
		sources: stub.mutations,
	}),
}));

import { m } from "$lib/paraglide/messages";
import ContextSourcesEditorHarness from "./context-sources-editor-harness.svelte";

const seeded: ContextSource[] = [
	{
		id: 1,
		label: "Мой профиль",
		url: "https://github.com/octocat",
		description: null,
		kind: "github",
		status: "ok",
		error: null,
		fetched_at: "2026-08-01T12:00:00Z",
		created_at: "2026-07-01T12:00:00Z",
	},
	{
		id: 2,
		label: "Портфолио",
		url: "https://octocat.dev",
		description: "Личный сайт",
		kind: "web",
		status: "error",
		error: "Timeout",
		fetched_at: null,
		created_at: "2026-07-02T12:00:00Z",
	},
];

function seedSources(data: ContextSource[]) {
	stub.sourcesQuery.mockReturnValue({
		data,
		isPending: false,
		isError: false,
		refetch: vi.fn(),
	});
}

function renderEditor() {
	return render(ContextSourcesEditorHarness);
}

beforeEach(() => {
	stub.sourcesQuery.mockReset();
	for (const mutation of Object.values(stub.mutations)) {
		mutation.mutate.mockReset();
	}
	seedSources(seeded);
});

describe("<ContextSourcesEditor>", () => {
	it("renders every seeded source by label", () => {
		renderEditor();

		expect(screen.getByText("Мой профиль")).toBeInTheDocument();
		expect(screen.getByText("Портфолио")).toBeInTheDocument();
	});

	it("shows the status badge text for ok and error rows, and the row error", () => {
		renderEditor();

		expect(
			screen.getByText(m.settings_ai_sources_status_ok()),
		).toBeInTheDocument();
		expect(
			screen.getByText(m.settings_ai_sources_status_error()),
		).toBeInTheDocument();
		expect(screen.getByText("Timeout")).toBeInTheDocument();
	});

	it("submitting the add form calls add.mutate with the entered fields", async () => {
		const user = userEvent.setup();
		renderEditor();

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
			"Хабр",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_url_field()),
			"https://habr.com/u/octocat",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_description_field()),
			"Блог",
		);
		await user.click(
			screen.getByRole("button", { name: m.settings_ai_sources_add() }),
		);

		expect(stub.mutations.add.mutate.mock.calls[0]?.[0]).toEqual({
			label: "Хабр",
			url: "https://habr.com/u/octocat",
			description: "Блог",
		});
	});

	it("clicking a row's delete button calls remove.mutate with its id", async () => {
		const user = userEvent.setup();
		renderEditor();

		const buttons = screen.getAllByRole("button", {
			name: m.settings_ai_sources_delete(),
		});
		await user.click(buttons[0]);

		expect(stub.mutations.remove.mutate).toHaveBeenCalledWith(1);
	});

	it("clicking a row's refresh button calls refresh.mutate with its id", async () => {
		const user = userEvent.setup();
		renderEditor();

		const buttons = screen.getAllByRole("button", {
			name: m.settings_ai_sources_refresh(),
		});
		await user.click(buttons[1]);

		expect(stub.mutations.refresh.mutate).toHaveBeenCalledWith(2);
	});

	it("clicking «Обновить все» calls refreshAll.mutate", async () => {
		const user = userEvent.setup();
		renderEditor();

		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_refresh_all(),
			}),
		);

		expect(stub.mutations.refreshAll.mutate).toHaveBeenCalled();
	});
});

describe("<ContextSourcesEditor> — empty state", () => {
	it("shows the empty placeholder when there are no sources", () => {
		seedSources([]);
		renderEditor();

		expect(screen.getByText(m.settings_ai_sources_empty())).toBeInTheDocument();
	});
});
