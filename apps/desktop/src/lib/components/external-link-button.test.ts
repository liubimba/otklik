import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { createRawSnippet } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

const openExternalSpy = vi.fn();

import ExternalLinkButton from "./external-link-button.svelte";

const label = createRawSnippet(() => ({ render: () => "<span>open</span>" }));

describe("<ExternalLinkButton>", () => {
	beforeEach(() => {
		openExternalSpy.mockReset();
		openExternalSpy.mockResolvedValue(undefined);
		vi.stubGlobal("otklik", { openExternal: openExternalSpy });
	});

	it("opens the href in the system browser on click", async () => {
		render(ExternalLinkButton, {
			href: "https://console.groq.com/keys",
			ariaLabel: "open",
			children: label,
		});

		await userEvent.setup().click(screen.getByRole("button", { name: "open" }));

		expect(openExternalSpy).toHaveBeenCalledWith(
			"https://console.groq.com/keys",
		);
	});
});
