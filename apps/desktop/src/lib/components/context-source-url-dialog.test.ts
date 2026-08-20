import type { ContextSource } from "$lib/api/types";
import { m } from "$lib/paraglide/messages";
import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ContextSourceUrlDialog from "./context-source-url-dialog.svelte";

function makeMutation() {
	return { mutate: vi.fn(), isPending: false };
}

function renderDialog(props: {
	add?: ReturnType<typeof makeMutation>;
	update?: ReturnType<typeof makeMutation>;
	source?: ContextSource | null;
}) {
	return render(ContextSourceUrlDialog, {
		open: true,
		add: props.add ?? makeMutation(),
		update: props.update ?? makeMutation(),
		source: props.source ?? null,
	});
}

const webSource: ContextSource = {
	id: 7,
	label: "My site",
	url: "https://example.com",
	description: "existing description",
	kind: "web",
	status: "ok",
	error: null,
	fetched_at: null,
	created_at: "2026-01-01T00:00:00Z",
	config: null,
	has_token: false,
};

beforeEach(() => {
	document.body.innerHTML = "";
});

describe("<ContextSourceUrlDialog> add mode", () => {
	it("calls add.mutate with kind github for a github.com url", async () => {
		const user = userEvent.setup();
		const add = makeMutation();
		renderDialog({ add });

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
			"My GitHub",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_url_field()),
			"https://github.com/x",
		);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_url_dialog_submit_add(),
			}),
		);

		expect(add.mutate.mock.calls[0]?.[0]).toEqual({
			label: "My GitHub",
			kind: "github",
			url: "https://github.com/x",
			description: null,
		});
	});

	it("calls add.mutate with kind web for a non-github url", async () => {
		const user = userEvent.setup();
		const add = makeMutation();
		renderDialog({ add });

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
			"My site",
		);
		await user.type(
			screen.getByLabelText(m.settings_ai_sources_url_field()),
			"https://example.com",
		);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_url_dialog_submit_add(),
			}),
		);

		expect(add.mutate.mock.calls[0]?.[0]).toEqual({
			label: "My site",
			kind: "web",
			url: "https://example.com",
			description: null,
		});
	});

	it("does not call add.mutate when label or url is empty", async () => {
		const user = userEvent.setup();
		const add = makeMutation();
		renderDialog({ add });

		await user.type(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
			"Only label",
		);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_url_dialog_submit_add(),
			}),
		);

		expect(add.mutate).not.toHaveBeenCalled();
	});
});

describe("<ContextSourceUrlDialog> edit mode", () => {
	it("prefills label, url and description from source", () => {
		renderDialog({ source: webSource });

		expect(
			screen.getByLabelText(m.settings_ai_sources_label_field()),
		).toHaveValue(webSource.label);
		expect(
			screen.getByLabelText(m.settings_ai_sources_url_field()),
		).toHaveValue(webSource.url);
		expect(
			screen.getByLabelText(m.settings_ai_sources_description_field()),
		).toHaveValue(webSource.description);
	});

	it("calls update.mutate with the unchanged source kind", async () => {
		const user = userEvent.setup();
		const update = makeMutation();
		renderDialog({ source: webSource, update });

		const urlInput = screen.getByLabelText(m.settings_ai_sources_url_field());
		await user.clear(urlInput);
		await user.type(urlInput, "https://github.com/changed");
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_url_dialog_submit_edit(),
			}),
		);

		expect(update.mutate.mock.calls[0]?.[0]).toEqual({
			id: webSource.id,
			body: {
				label: webSource.label,
				kind: "web",
				url: "https://github.com/changed",
				description: webSource.description,
			},
		});
	});

	it("does not call update.mutate when the url is cleared", async () => {
		const user = userEvent.setup();
		const update = makeMutation();
		renderDialog({ source: webSource, update });

		const urlInput = screen.getByLabelText(m.settings_ai_sources_url_field());
		await user.clear(urlInput);
		await user.click(
			screen.getByRole("button", {
				name: m.settings_ai_sources_url_dialog_submit_edit(),
			}),
		);

		expect(update.mutate).not.toHaveBeenCalled();
	});
});
