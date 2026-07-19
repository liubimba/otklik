import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { createRawSnippet } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

const openUrl = vi.fn();
vi.mock("@tauri-apps/plugin-opener", () => ({
	openUrl: (url: string) => openUrl(url),
}));

import ExternalLinkButton from "./external-link-button.svelte";

const label = createRawSnippet(() => ({ render: () => "<span>open</span>" }));

describe("<ExternalLinkButton>", () => {
	beforeEach(() => {
		openUrl.mockReset();
		openUrl.mockResolvedValue(undefined);
	});

	it("opens the href in the system browser on click", async () => {
		render(ExternalLinkButton, {
			href: "https://console.groq.com/keys",
			ariaLabel: "open",
			children: label,
		});

		await userEvent.setup().click(screen.getByRole("button", { name: "open" }));

		expect(openUrl).toHaveBeenCalledWith("https://console.groq.com/keys");
	});
});
