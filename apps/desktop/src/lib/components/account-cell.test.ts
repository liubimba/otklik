import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import AccountCell from "./account-cell.svelte";

function noop() {}

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

	it("offline: shows 'Нет связи' and is NOT an interactive button — the backend is unreachable, so a click can't do anything (bug #2)", () => {
		render(AccountCell, {
			status: "offline",
			onSignIn: noop,
			onSignOut: noop,
			onCancel: noop,
		});

		expect(screen.getByText("Нет связи")).toBeInTheDocument();
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
			await userEvent.setup({ pointerEventsCheck: 0 }).click(signOutItem);

			expect(onSignOut).toHaveBeenCalledOnce();
		});
	});
});
