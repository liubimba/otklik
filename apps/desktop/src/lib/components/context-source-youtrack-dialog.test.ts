import { m } from "$lib/paraglide/messages";
import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ContextSourceYoutrackDialog from "./context-source-youtrack-dialog.svelte";

function renderDialog(add: {
	mutate: ReturnType<typeof vi.fn>;
	isPending: boolean;
}) {
	return render(ContextSourceYoutrackDialog, { open: true, add });
}

function makeAdd() {
	return { mutate: vi.fn(), isPending: false };
}

beforeEach(() => {
	document.body.innerHTML = "";
});

describe("<ContextSourceYoutrackDialog>", () => {
	it("renders label, base_url, token, query and description fields", () => {
		renderDialog(makeAdd());

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
		renderDialog(makeAdd());

		const tokenInput = screen.getByLabelText(
			m.settings_ai_sources_youtrack_token_field(),
		);
		expect(tokenInput).toHaveAttribute("type", "password");
	});

	it("prefills the query field with the default 'for: me'", () => {
		renderDialog(makeAdd());

		const queryInput = screen.getByLabelText(
			m.settings_ai_sources_youtrack_query_field(),
		) as HTMLInputElement;
		expect(queryInput.value).toBe("for: me");
	});

	it("submitting the filled form calls add.mutate with kind, config and token", async () => {
		const user = userEvent.setup();
		const add = makeAdd();
		renderDialog(add);

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
		renderDialog(add);

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
});
