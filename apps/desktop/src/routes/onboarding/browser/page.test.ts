import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const goto = vi.fn();
vi.mock("$app/navigation", () => ({ goto: (url: string) => goto(url) }));

const chromium = vi.fn();
const state = vi.fn();
vi.mock("$lib/api/client", () => ({
	API: {
		setup: {
			chromium: () => chromium(),
			state: () => state(),
		},
	},
}));
vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

import * as m from "$lib/paraglide/messages";
import BrowserPage from "./+page.svelte";

async function* downloadTo(...percents: number[]) {
	for (const percent of percents) {
		yield { status: "downloading", percent, done: false };
	}
	yield { status: "done", percent: 100, done: true };
}

describe("<onboarding/browser>", () => {
	beforeEach(() => {
		goto.mockReset();
		chromium.mockReset();
		state.mockReset();
	});

	it("показывает прогресс загрузки в progressbar", async () => {
		state.mockResolvedValue({ chromium_installed: false });
		chromium.mockReturnValue(downloadTo(40));
		render(BrowserPage);

		const bar = await screen.findByRole("progressbar");
		expect(bar).toHaveAttribute("aria-valuenow", "100");
	});

	it("уводит на выбор модели, когда браузер готов", async () => {
		state.mockResolvedValue({ chromium_installed: true });
		render(BrowserPage);

		await vi.waitFor(() =>
			expect(goto).toHaveBeenCalledWith("/onboarding/model"),
		);
		expect(chromium).not.toHaveBeenCalled();
	});

	it("кнопка «Попробовать снова» действительно перезапускает загрузку", async () => {
		state.mockResolvedValue({ chromium_installed: false });
		chromium.mockImplementationOnce(() => {
			throw new Error("network is down");
		});
		render(BrowserPage);

		expect(await screen.findByText("network is down")).toBeInTheDocument();
		expect(goto).not.toHaveBeenCalled();

		chromium.mockReturnValue(downloadTo(100));
		await userEvent
			.setup()
			.click(screen.getByRole("button", { name: m.setup_retry() }));

		await vi.waitFor(() =>
			expect(goto).toHaveBeenCalledWith("/onboarding/model"),
		);
	});
});
