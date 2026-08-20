import type { ContextSource } from "$lib/api/types";
import { cleanup, render, screen, waitFor } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const stub = vi.hoisted(() => ({
	sourcesQuery: vi.fn(),
	mutations: {
		add: { mutate: vi.fn(), isPending: false },
		update: { mutate: vi.fn(), isPending: false },
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
		config: null,
		has_token: false,
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
		config: null,
		has_token: false,
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

afterEach(() => {
	cleanup();
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

	it("does not render its own <form> element so it is safe inside the settings form", () => {
		const { container } = renderEditor();

		expect(container.querySelector("form")).toBeNull();
	});

	it("clicking «Добавить источник» opens the URL dialog in add mode", async () => {
		const user = userEvent.setup();
		renderEditor();

		await user.click(
			screen.getByRole("button", { name: m.settings_ai_sources_add() }),
		);

		expect(
			await screen.findByRole("heading", {
				name: m.settings_ai_sources_url_dialog_add_title(),
			}),
		).toBeInTheDocument();
		await waitFor(() =>
			expect(
				(
					screen.getByLabelText(
						m.settings_ai_sources_label_field(),
					) as HTMLInputElement
				).value,
			).toBe(""),
		);
	});

	it("clicking a web row's edit button opens the URL dialog with that source", async () => {
		const user = userEvent.setup();
		renderEditor();

		const editButtons = screen.getAllByRole("button", {
			name: m.settings_ai_sources_edit(),
		});
		await user.click(editButtons[1]);

		expect(
			await screen.findByRole("heading", {
				name: m.settings_ai_sources_url_dialog_edit_title(),
			}),
		).toBeInTheDocument();
		await waitFor(() =>
			expect(
				(
					screen.getByLabelText(
						m.settings_ai_sources_label_field(),
					) as HTMLInputElement
				).value,
			).toBe("Портфолио"),
		);
	});

	it("clicking a youtrack row's edit button opens the YouTrack dialog with that source", async () => {
		const user = userEvent.setup();
		seedSources([
			...seeded,
			{
				id: 3,
				label: "Мои задачи",
				url: "https://example.youtrack.cloud",
				description: null,
				kind: "youtrack",
				status: "ok",
				error: null,
				fetched_at: null,
				created_at: "2026-07-03T12:00:00Z",
				config: {
					base_url: "https://example.youtrack.cloud",
					query: "for: me",
				},
				has_token: true,
			},
		]);
		renderEditor();

		const editButtons = screen.getAllByRole("button", {
			name: m.settings_ai_sources_edit(),
		});
		await user.click(editButtons[2]);

		expect(
			await screen.findByRole("heading", {
				name: m.settings_ai_sources_youtrack_edit_title(),
			}),
		).toBeInTheDocument();
		await waitFor(() =>
			expect(
				(
					screen.getByLabelText(
						m.settings_ai_sources_label_field(),
					) as HTMLInputElement
				).value,
			).toBe("Мои задачи"),
		);
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
