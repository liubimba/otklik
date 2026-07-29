import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const goto = vi.fn();
vi.mock("$app/navigation", () => ({ goto: (url: string) => goto(url) }));

const saveConsent = vi.fn();
vi.mock("$lib/consent", () => ({
	saveConsent: (value: boolean) => saveConsent(value),
}));

const closeWindow = vi.fn();
vi.mock("@tauri-apps/api/window", () => ({
	getCurrentWindow: () => ({ close: () => closeWindow() }),
}));

vi.mock("@tauri-apps/plugin-log", () => ({ info: vi.fn(), error: vi.fn() }));

import * as m from "$lib/paraglide/messages";
import ConsentPage from "./+page.svelte";

describe("<onboarding> consent gate", () => {
	beforeEach(() => {
		goto.mockReset();
		saveConsent.mockReset();
		closeWindow.mockReset();
	});

	it("Escape не закрывает окно — согласие это жёсткий гейт, а не попап", async () => {
		render(ConsentPage);
		await screen.findByRole("dialog");

		await userEvent.setup().keyboard("{Escape}");

		expect(closeWindow).not.toHaveBeenCalled();
	});

	it("кнопка «Отклонить» закрывает окно", async () => {
		render(ConsentPage);
		await screen.findByRole("dialog");

		await userEvent
			.setup()
			.click(screen.getByRole("button", { name: m.onboarding_decline() }));

		expect(closeWindow).toHaveBeenCalledOnce();
	});

	it("кнопка «Принять» сохраняет согласие и ведёт дальше, окно не закрывает", async () => {
		saveConsent.mockResolvedValue(undefined);
		render(ConsentPage);
		await screen.findByRole("dialog");

		await userEvent
			.setup()
			.click(screen.getByRole("button", { name: m.onboarding_accept() }));

		await vi.waitFor(() => expect(saveConsent).toHaveBeenCalledWith(true));
		expect(goto).toHaveBeenCalledWith("/onboarding/browser");
		expect(closeWindow).not.toHaveBeenCalled();
	});
});
