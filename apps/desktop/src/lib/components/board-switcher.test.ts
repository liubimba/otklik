import { m } from "$lib/paraglide/messages";
import { cleanup, render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import BoardSwitcher from "./board-switcher.svelte";

afterEach(() => {
	cleanup();
});

describe("<BoardSwitcher>", () => {
	it("renders a tab per board and marks the active one selected", () => {
		render(BoardSwitcher, { active: "hh_ru", onSelect: vi.fn() });

		const hh = screen.getByRole("tab", { name: m.queue_board_hh_ru() });
		const habr = screen.getByRole("tab", {
			name: (name) => name.includes(m.queue_board_habr()),
		});
		expect(hh).toHaveAttribute("aria-selected", "true");
		expect(habr).toHaveAttribute("aria-selected", "false");
	});

	it("shows no «Скоро» badge while both boards are enabled", () => {
		render(BoardSwitcher, { active: "hh_ru", onSelect: vi.fn() });
		expect(
			screen.queryByText(m.board_badge_coming_soon()),
		).not.toBeInTheDocument();
	});

	it("selecting a board calls onSelect with its kind", async () => {
		const onSelect = vi.fn();
		render(BoardSwitcher, { active: "hh_ru", onSelect });

		await userEvent.setup().click(
			screen.getByRole("tab", {
				name: (name) => name.includes(m.queue_board_habr()),
			}),
		);

		expect(onSelect).toHaveBeenCalledWith("habr");
	});
});
