import Inbox from "@lucide/svelte/icons/inbox";
import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import SidebarNavRow from "./sidebar-nav-row.svelte";

describe("<SidebarNavRow>", () => {
	it("does not render the counter when count is 0", () => {
		render(SidebarNavRow, {
			href: "/queue",
			label: "Очередь вакансий",
			icon: Inbox,
			active: false,
			count: 0,
		});

		expect(screen.queryByTestId("nav-row-count")).not.toBeInTheDocument();
	});

	it("does not render the counter when count is null", () => {
		render(SidebarNavRow, {
			href: "/queue",
			label: "Очередь вакансий",
			icon: Inbox,
			active: false,
			count: null,
		});

		expect(screen.queryByTestId("nav-row-count")).not.toBeInTheDocument();
	});

	it("renders the counter showing 12 when count is 12", () => {
		render(SidebarNavRow, {
			href: "/queue",
			label: "Очередь вакансий",
			icon: Inbox,
			active: false,
			count: 12,
		});

		expect(screen.getByText("12")).toBeInTheDocument();
	});

	it("sets aria-current=page only when active is true", () => {
		render(SidebarNavRow, {
			href: "/queue",
			label: "Очередь вакансий",
			icon: Inbox,
			active: true,
		});

		expect(screen.getByRole("link")).toHaveAttribute("aria-current", "page");
	});

	it("does not set aria-current when active is false", () => {
		render(SidebarNavRow, {
			href: "/queue",
			label: "Очередь вакансий",
			icon: Inbox,
			active: false,
		});

		expect(screen.getByRole("link")).not.toHaveAttribute("aria-current");
	});
});
