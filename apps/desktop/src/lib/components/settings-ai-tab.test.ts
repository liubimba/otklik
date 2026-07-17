import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("$lib/queries", () => ({
	query: {
		settings: {
			create: () => ({ data: { probe: "initial" } }),
		},
		secret_storage: {
			create: () => ({ data: { mode: "keychain" } }),
		},
	},
}));

import { m } from "$lib/paraglide/messages";
import type { LLMDeploymentForm } from "$lib/schemas/settings";
import SettingsAiTabHarness from "./settings-ai-tab-harness.svelte";

const storedDeployment: LLMDeploymentForm = {
	id: "dep-1",
	model: "openai/gpt-4o",
	api_base: "",
	has_api_key: true,
	api_key: "",
	clear_api_key: false,
};

function renderStoredDeployment() {
	return render(SettingsAiTabHarness, {
		deployments: [{ ...storedDeployment }],
	});
}

async function openDeploymentRow(): Promise<
	ReturnType<typeof userEvent.setup>
> {
	const user = userEvent.setup();
	await user.click(screen.getByRole("button", { name: /openai\/gpt-4o/ }));
	return user;
}

describe("<SettingsAiTab> — API key field for a stored deployment", () => {
	it("(a) initially shows the stored affordance and no password input", async () => {
		renderStoredDeployment();
		await openDeploymentRow();

		expect(
			await screen.findByText(m.settings_ai_key_stored()),
		).toBeInTheDocument();
		expect(
			screen.queryByPlaceholderText(m.settings_ai_key_placeholder()),
		).not.toBeInTheDocument();
	});

	it("(b) clicking «Заменить» renders a password input (fails without the untrack fix)", async () => {
		renderStoredDeployment();
		const user = await openDeploymentRow();

		await user.click(
			screen.getByRole("button", { name: m.settings_ai_key_replace() }),
		);

		expect(
			await screen.findByPlaceholderText(m.settings_ai_key_placeholder()),
		).toBeInTheDocument();
		expect(
			screen.queryByText(m.settings_ai_key_stored()),
		).not.toBeInTheDocument();
	});

	it("(c) clicking «Удалить» marks the key for deletion", async () => {
		renderStoredDeployment();
		const user = await openDeploymentRow();

		await user.click(
			screen.getByRole("button", { name: m.settings_ai_key_remove() }),
		);

		expect(
			await screen.findByText(m.settings_ai_key_will_be_removed()),
		).toBeInTheDocument();
	});
});
