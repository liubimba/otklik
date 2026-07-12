import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AccountCell from "./account-cell.svelte";

function noop() {}

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

	it("unauthorized: shows the status text and clicking calls onSignIn", async () => {
		const onSignIn = vi.fn();
		render(AccountCell, {
			status: "unauthorized",
			onSignIn,
			onSignOut: noop,
			onCancel: noop,
		});

		expect(screen.getByText("Не подключён")).toBeInTheDocument();

		await userEvent.setup().click(screen.getByRole("button"));
		expect(onSignIn).toHaveBeenCalledOnce();
	});

	it("authorizing: clicking calls onCancel", async () => {
		const onCancel = vi.fn();
		render(AccountCell, {
			status: "authorizing",
			onSignIn: noop,
			onSignOut: noop,
			onCancel,
		});

		expect(screen.getByText("Подключаем…")).toBeInTheDocument();

		await userEvent.setup().click(screen.getByRole("button"));
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it("authorized: clicking calls onSignOut", async () => {
		const onSignOut = vi.fn();
		render(AccountCell, {
			status: "authorized",
			onSignIn: noop,
			onSignOut,
			onCancel: noop,
		});

		expect(screen.getByText("Подключён")).toBeInTheDocument();

		await userEvent.setup().click(screen.getByRole("button"));
		expect(onSignOut).toHaveBeenCalledOnce();
	});
});
