import type { BoardPrompt } from "$lib/api/types";
import { m } from "$lib/paraglide/messages";
import { cleanup, render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import BoardPromptPanel from "./board-prompt-panel.svelte";

afterEach(() => {
	cleanup();
});

function open() {
	return userEvent
		.setup()
		.click(screen.getByRole("button", { expanded: false }));
}

describe("<BoardPromptPanel>", () => {
	it("stays collapsed until its header is clicked", () => {
		render(BoardPromptPanel, {
			active: "kwork",
			value: undefined,
			pending: false,
			onSave: vi.fn(),
		});
		expect(
			screen.queryByPlaceholderText(m.queue_board_prompt_placeholder()),
		).not.toBeInTheDocument();
	});

	it("marks a board that already has a prompt with the «Задан» badge", () => {
		render(BoardPromptPanel, {
			active: "kwork",
			value: { mode: "replace", text: "Отклик" } satisfies BoardPrompt,
			pending: false,
			onSave: vi.fn(),
		});
		expect(
			screen.getByText(m.queue_board_prompt_active_badge()),
		).toBeInTheDocument();
	});

	it("keeps save disabled until the text changes", async () => {
		render(BoardPromptPanel, {
			active: "kwork",
			value: undefined,
			pending: false,
			onSave: vi.fn(),
		});
		await open();

		const save = screen.getByRole("button", {
			name: m.queue_board_prompt_save(),
		});
		expect(save).toBeDisabled();

		await userEvent
			.setup()
			.type(
				screen.getByPlaceholderText(m.queue_board_prompt_placeholder()),
				"Пиши как бид",
			);
		expect(save).toBeEnabled();
	});

	it("saves the trimmed draft with the chosen mode", async () => {
		const onSave = vi.fn();
		render(BoardPromptPanel, {
			active: "kwork",
			value: undefined,
			pending: false,
			onSave,
		});
		await open();

		await userEvent
			.setup()
			.type(
				screen.getByPlaceholderText(m.queue_board_prompt_placeholder()),
				"  Пиши как бид  ",
			);
		await userEvent
			.setup()
			.click(screen.getByRole("button", { name: m.queue_board_prompt_save() }));

		expect(onSave).toHaveBeenCalledWith({
			mode: "append",
			text: "Пиши как бид",
		});
	});
});
