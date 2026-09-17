import { m } from "$lib/paraglide/messages";
import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import NewSearchButton from "./new-search-button.svelte";

afterEach(() => {
	document.body.style.pointerEvents = "";
	document.body.removeAttribute("data-scroll-locked");
});

async function openMenu() {
	await userEvent
		.setup()
		.click(screen.getByRole("button", { name: m.queue_button_new_search() }));
}

describe("<NewSearchButton>", () => {
	it("choosing the hh.ru board calls onSelect with hh_ru", async () => {
		const onSelect = vi.fn();
		render(NewSearchButton, { onSelect });

		await openMenu();
		const item = await screen.findByRole("menuitem", {
			name: m.queue_board_hh_ru(),
		});
		await userEvent.setup({ pointerEventsCheck: 0 }).click(item);

		expect(onSelect).toHaveBeenCalledOnce();
		expect(onSelect).toHaveBeenCalledWith("hh_ru");
	});

	it("the Хабр Карьера board is disabled and marked «Скоро», and choosing it does nothing", async () => {
		const onSelect = vi.fn();
		render(NewSearchButton, { onSelect });

		await openMenu();
		const item = await screen.findByRole("menuitem", {
			name: (name) => name.includes(m.queue_board_habr()),
		});

		expect(item).toHaveAttribute("aria-disabled", "true");
		expect(screen.getByText(m.board_badge_coming_soon())).toBeInTheDocument();

		await userEvent.setup({ pointerEventsCheck: 0 }).click(item);
		expect(onSelect).not.toHaveBeenCalled();
	});

	it("a disabled trigger cannot open the menu", async () => {
		const onSelect = vi.fn();
		render(NewSearchButton, { onSelect, disabled: true });

		await openMenu();

		expect(
			screen.queryByRole("menuitem", { name: m.queue_board_hh_ru() }),
		).not.toBeInTheDocument();
	});
});
