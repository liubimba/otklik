import { m } from "$lib/paraglide/messages";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";

import KworkPricePanel from "./kwork-price-panel.svelte";

afterEach(() => {
	cleanup();
});

describe("<KworkPricePanel>", () => {
	it("shows the current percent", () => {
		render(KworkPricePanel, { percent: 40, pending: false, onSave: vi.fn() });
		expect(screen.getByText("40%")).toBeInTheDocument();
		expect(screen.getByRole("slider")).toHaveValue("40");
	});

	it("commits the new value on change", async () => {
		const onSave = vi.fn();
		render(KworkPricePanel, { percent: 0, pending: false, onSave });

		const slider = screen.getByRole("slider");
		await fireEvent.change(slider, { target: { value: "75" } });

		expect(onSave).toHaveBeenCalledWith(75);
	});

	it("does not save when the value is unchanged", async () => {
		const onSave = vi.fn();
		render(KworkPricePanel, { percent: 25, pending: false, onSave });

		const slider = screen.getByRole("slider");
		await fireEvent.change(slider, { target: { value: "25" } });

		expect(onSave).not.toHaveBeenCalled();
	});
});
