import type { ContextSource } from "$lib/api/types";
import { m } from "$lib/paraglide/messages";
import { cleanup, render, screen, waitFor } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ContextSourceYoutrackDialog from "./context-source-youtrack-dialog.svelte";

function makeAdd() {
	return { mutate: vi.fn(), isPending: false };
}

function makeUpdate() {
	return { mutate: vi.fn(), isPending: false };
}

function makeSource(overrides: Partial<ContextSource> = {}): ContextSource {
	return {
		id: 7,
		label: "Мои задачи",
		url: "https://example.youtrack.cloud",
		description: "Личная очередь",
		kind: "youtrack",
		status: "ok",
		error: null,
		fetched_at: null,
		created_at: "2026-01-01T00:00:00Z",
		config: { base_url: "https://example.youtrack.cloud", query: "for: me" },
		has_token: true,
		...overrides,
	};
}

function renderDialog(
	props: {
		add?: ReturnType<typeof makeAdd>;
		update?: ReturnType<typeof makeUpdate>;
		source?: ContextSource | null;
	} = {},
) {
	return render(ContextSourceYoutrackDialog, {
		open: true,
		add: props.add ?? makeAdd(),
		update: props.update ?? makeUpdate(),
		source: props.source ?? null,
	});
}

async function settleInitialFocus() {
	await waitFor(() =>
		expect((document.activeElement as HTMLElement | null)?.id).toBe(
			"youtrack-source-label",
		),
	);
}

afterEach(() => {
	cleanup();
});

describe("<ContextSourceYoutrackDialog> add mode", () => {
	it("renders label, base_url, token, query and description fields", () => {
		renderDialog();

		expect(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
		).toBeInTheDocument();
		expect(
			screen.getByLabelText(m.settings_ai_sources_youtrack_base_url_field()),
		).toBeInTheDocument();
		expect(
			screen.getByLabelText(m.settings_ai_sources_youtrack_token_field()),
		).toBeInTheDocument();
		expect(
			screen.getByLabelText(m.settings_ai_sources_youtrack_query_field()),
		).toBeInTheDocument();
		expect(
			screen.getByLabelText(m.settings_ai_sources_description_field()),
		).toBeInTheDocument();
	});

	it("masks the token field as a password input", () => {
		renderDialog();

		const tokenInput = screen.getByLabelText(
			m.settings_ai_sources_youtrack_token_field(),
		);
		expect(tokenInput).toHaveAttribute("type", "password");
	});

	it("prefills the query field with the default 'for: me'", () => {
		renderDialog();

		const queryInput = screen.getByLabelText(
			m.settings_ai_sources_youtrack_query_field(),
		) as HTMLInputElement;
		expect(queryInput.value).toBe("for: me");
	});

	it("shows the add title", () => {
		renderDialog();

		expect(
			screen.getByText(m.settings_ai_sources_youtrack_title()),
		).toBeInTheDocument();
	});

	it("submitting the filled form calls add.mutate with kind, config and token", async () => {
		const user = userEvent.setup();
		const add = makeAdd();
		renderDialog({ add });
		await settleInitialFocus();

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
			"Мои задачи",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_youtrack_base_url_field()),
			"https://example.youtrack.cloud",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_youtrack_token_field()),
			"secret-token",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_description_field()),
			"Личная очередь",
		);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_youtrack_submit(),
			}),
		);

		expect(add.mutate.mock.calls[0]?.[0]).toEqual({
			kind: "youtrack",
			label: "Мои задачи",
			description: "Личная очередь",
			config: { base_url: "https://example.youtrack.cloud", query: "for: me" },
			token: "secret-token",
		});
	});

	it("does not call add.mutate when a required field is empty", async () => {
		const user = userEvent.setup();
		const add = makeAdd();
		renderDialog({ add });
		await settleInitialFocus();

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
			"Мои задачи",
		);

		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_youtrack_submit(),
			}),
		);

		expect(add.mutate).not.toHaveBeenCalled();
	});

	it("does not show a clear-token checkbox or has-token indicator", () => {
		renderDialog();

		expect(
			screen.queryByText(m.settings_ai_sources_youtrack_clear_token()),
		).not.toBeInTheDocument();
		expect(
			screen.queryByText(m.settings_ai_sources_youtrack_has_token()),
		).not.toBeInTheDocument();
	});
});

describe("<ContextSourceYoutrackDialog> edit mode", () => {
	it("shows the edit title", () => {
		renderDialog({ source: makeSource() });

		expect(
			screen.getByText(m.settings_ai_sources_youtrack_edit_title()),
		).toBeInTheDocument();
	});

	it("prefills label, description, base_url and query from the source", () => {
		renderDialog({ source: makeSource() });

		expect(
			(
				screen.getByLabelText(
					m.settings_ai_sources_label_field(),
				) as HTMLInputElement
			).value,
		).toBe("Мои задачи");
		expect(
			(
				screen.getByLabelText(
					m.settings_ai_sources_youtrack_base_url_field(),
				) as HTMLInputElement
			).value,
		).toBe("https://example.youtrack.cloud");
		expect(
			(
				screen.getByLabelText(
					m.settings_ai_sources_youtrack_query_field(),
				) as HTMLInputElement
			).value,
		).toBe("for: me");
		expect(
			(
				screen.getByLabelText(
					m.settings_ai_sources_description_field(),
				) as HTMLInputElement
			).value,
		).toBe("Личная очередь");
	});

	it("leaves the token field empty and shows the has-token indicator when the source has a token", () => {
		renderDialog({ source: makeSource({ has_token: true }) });

		const tokenInput = screen.getByLabelText(
			m.settings_ai_sources_youtrack_token_field(),
		) as HTMLInputElement;
		expect(tokenInput.value).toBe("");
		expect(tokenInput).toHaveAttribute("type", "password");
		expect(
			screen.getByText(m.settings_ai_sources_youtrack_has_token()),
		).toBeInTheDocument();
	});

	it("does not show the has-token indicator or clear checkbox when the source has no token", () => {
		renderDialog({ source: makeSource({ has_token: false }) });

		expect(
			screen.queryByText(m.settings_ai_sources_youtrack_has_token()),
		).not.toBeInTheDocument();
		expect(
			screen.queryByText(m.settings_ai_sources_youtrack_clear_token()),
		).not.toBeInTheDocument();
	});

	it("submitting without typing a token keeps the stored token", async () => {
		const user = userEvent.setup();
		const update = makeUpdate();
		const source = makeSource();
		renderDialog({ update, source });
		await settleInitialFocus();

		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_youtrack_submit(),
			}),
		);

		expect(update.mutate.mock.calls[0]?.[0]).toEqual({
			id: source.id,
			body: {
				kind: "youtrack",
				label: "Мои задачи",
				description: "Личная очередь",
				config: {
					base_url: "https://example.youtrack.cloud",
					query: "for: me",
				},
				token: null,
				clear_token: false,
			},
		});
	});

	it("submitting after typing a new token replaces it", async () => {
		const user = userEvent.setup();
		const update = makeUpdate();
		const source = makeSource();
		renderDialog({ update, source });
		await settleInitialFocus();

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_youtrack_token_field()),
			"newtok",
		);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_youtrack_submit(),
			}),
		);

		expect(update.mutate.mock.calls[0]?.[0]?.body).toMatchObject({
			token: "newtok",
			clear_token: false,
		});
	});

	it("checking the clear-token checkbox clears the stored token and disables the token input", async () => {
		const user = userEvent.setup();
		const update = makeUpdate();
		const source = makeSource();
		renderDialog({ update, source });
		await settleInitialFocus();

		const checkbox = screen.getByLabelText(
			m.settings_ai_sources_youtrack_clear_token(),
		);
		await user.click(checkbox);

		const tokenInput = screen.getByLabelText(
			m.settings_ai_sources_youtrack_token_field(),
		) as HTMLInputElement;
		expect(tokenInput).toBeDisabled();

		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_youtrack_submit(),
			}),
		);

		expect(update.mutate.mock.calls[0]?.[0]?.body).toMatchObject({
			token: null,
			clear_token: true,
		});
	});

	it("does not call update.mutate when label is cleared", async () => {
		const user = userEvent.setup();
		const update = makeUpdate();
		renderDialog({ update, source: makeSource() });
		await settleInitialFocus();

		const labelInput = screen.getByLabelText(
			m.settings_ai_sources_label_field(),
		);
		await user.clear(labelInput);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_youtrack_submit(),
			}),
		);

		expect(update.mutate).not.toHaveBeenCalled();
	});

	it("does not require a token to submit", () => {
		renderDialog({ source: makeSource({ has_token: false }) });

		const submitButton = screen.getByRole("button", {
			name: m.settings_ai_sources_youtrack_submit(),
		});
		expect(submitButton).not.toBeDisabled();
	});
});
