import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import AccountCell from "./account-cell.svelte";

function noop() {}

// bits-ui locks scroll on <body> (pointer-events: none, among other things)
// while the dropdown is open, and reverts it on close/unmount. When a test
// ends with the menu still open, testing-library's auto-cleanup unmounts
// the component but that revert doesn't always land before jsdom moves on,
// so the lock can leak into the next test's fresh render. Reset it
// explicitly so tests stay order-independent.
afterEach(() => {
	document.body.style.pointerEvents = "";
	document.body.removeAttribute("data-scroll-locked");
});

describe("<AccountCell>", () => {
	it("loading: renders a skeleton and no button", () => {
		render(AccountCell, {
			status: "loading",
			onSignIn: noop,
			onSignOut: noop,
			onCancel: noop,
		});

		expect(screen.queryByRole("button")).not.toBeInTheDocument();
	});

	it("unauthorized: shows the status text, has an accessible name naming the action, and clicking calls onSignIn directly", async () => {
		const onSignIn = vi.fn();
		render(AccountCell, {
			status: "unauthorized",
			onSignIn,
			onSignOut: noop,
			onCancel: noop,
		});

		expect(screen.getByText("Не подключён")).toBeInTheDocument();

		const button = screen.getByRole("button", { name: "Войти в hh.ru" });
		await userEvent.setup().click(button);
		expect(onSignIn).toHaveBeenCalledOnce();
	});

	it("authorizing: has an accessible name naming the action, and clicking calls onCancel directly", async () => {
		const onCancel = vi.fn();
		render(AccountCell, {
			status: "authorizing",
			onSignIn: noop,
			onSignOut: noop,
			onCancel,
		});

		expect(screen.getByText("Подключаем…")).toBeInTheDocument();

		const button = screen.getByRole("button", { name: "Отменить подключение" });
		await userEvent.setup().click(button);
		expect(onCancel).toHaveBeenCalledOnce();
	});

	// Signing out drops the persistent hh.ru session — it must never fire on a
	// bare click. Clicking the cell only OPENS a menu; onSignOut fires only
	// when the «Выйти» item inside it is chosen. bits-ui portals the menu
	// content to document.body, but `screen` queries the whole document, so
	// no special wiring is needed to find it once open.
	describe("authorized", () => {
		it("shows the status text and has an accessible name naming the menu, not the sign-out action", () => {
			render(AccountCell, {
				status: "authorized",
				onSignIn: noop,
				onSignOut: noop,
				onCancel: noop,
			});

			expect(screen.getByText("Подключён")).toBeInTheDocument();
			expect(
				screen.getByRole("button", { name: "Открыть меню аккаунта" }),
			).toBeInTheDocument();
		});

		it("clicking the cell does NOT call onSignOut", async () => {
			const onSignOut = vi.fn();
			render(AccountCell, {
				status: "authorized",
				onSignIn: noop,
				onSignOut,
				onCancel: noop,
			});

			await userEvent
				.setup()
				.click(screen.getByRole("button", { name: "Открыть меню аккаунта" }));
			expect(onSignOut).not.toHaveBeenCalled();
		});

		it("opens a menu with «Выйти», and choosing it calls onSignOut", async () => {
			const onSignOut = vi.fn();
			render(AccountCell, {
				status: "authorized",
				onSignIn: noop,
				onSignOut,
				onCancel: noop,
			});

			const user = userEvent.setup();
			await user.click(
				screen.getByRole("button", { name: "Открыть меню аккаунта" }),
			);

			const signOutItem = await screen.findByRole("menuitem", {
				name: "Выйти",
			});
			// bits-ui sets `pointer-events: none` on the trigger while the menu is
			// open (real browsers respect layout, so the open item is never
			// actually behind it) — but jsdom gives every element 0x0 layout, so
			// userEvent's realistic pointer-path hit-test sees the trigger
			// "underneath" the item at (0,0) and refuses to click. Disable that
			// check for this one interaction rather than fight jsdom's layout.
			await userEvent.setup({ pointerEventsCheck: 0 }).click(signOutItem);

			expect(onSignOut).toHaveBeenCalledOnce();
		});
	});
});
