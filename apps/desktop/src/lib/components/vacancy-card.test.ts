import { render, screen } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Vacancy } from "$lib/api/types";
import VacancyCard from "./vacancy-card.svelte";

function vacancy(overrides: Partial<Vacancy> = {}): Vacancy {
	return {
		id: 1,
		title: "Backend engineer",
		apply_link: "https://hh.ru/vacancy/1",
		description: "Great vacancy",
		response_link: null,
		company_stars: null,
		salary: null,
		company_name: null,
		work_location: null,
		updated_at: null,
		published_at: null,
		work_formats: [],
		employment_types: [],
		work_experience: null,
		...overrides,
	};
}

describe("<VacancyCard>", () => {
	it("renders the title", () => {
		render(VacancyCard, { vacancy: vacancy({ title: "Rust developer" }) });
		expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
			"Rust developer",
		);
	});

	it("renders company_name / salary / work_location when present", () => {
		render(VacancyCard, {
			vacancy: vacancy({
				company_name: "Yandex",
				salary: "500k",
				work_location: "Moscow",
			}),
		});
		expect(screen.getByText("Yandex")).toBeInTheDocument();
		expect(screen.getByText("500k")).toBeInTheDocument();
		expect(screen.getByText("Moscow")).toBeInTheDocument();
	});

	it("hides company_name / salary / work_location when null", () => {
		render(VacancyCard, {
			vacancy: vacancy({
				company_name: null,
				salary: null,
				work_location: null,
			}),
		});
		expect(screen.queryByText("Yandex")).not.toBeInTheDocument();
		// No <p> siblings apart from the heading
		expect(screen.queryAllByRole("paragraph")).toEqual([]);
	});

	it("apply_link points to the vacancy URL and opens in a new tab safely", () => {
		render(VacancyCard, {
			vacancy: vacancy({ apply_link: "https://hh.ru/vacancy/42" }),
		});
		const link = screen.getByRole("link");
		expect(link).toHaveAttribute("href", "https://hh.ru/vacancy/42");
		expect(link).toHaveAttribute("target", "_blank");
		expect(link).toHaveAttribute("rel", "noopener noreferrer");
	});

	it("clicking the card invokes onclick with the vacancy", async () => {
		const onclick = vi.fn();
		const v = vacancy({ id: 77 });
		render(VacancyCard, { vacancy: v, onclick });

		const card = screen.getByRole("button");
		await userEvent.setup().click(card);

		expect(onclick).toHaveBeenCalledWith(v);
	});

	it("clicking the external link does NOT propagate to the card handler", async () => {
		const onclick = vi.fn();
		render(VacancyCard, { vacancy: vacancy(), onclick });

		await userEvent.setup().click(screen.getByRole("link"));
		expect(onclick).not.toHaveBeenCalled();
	});

	it("Enter on a focused card triggers onclick", async () => {
		const onclick = vi.fn();
		const v = vacancy({ id: 3 });
		render(VacancyCard, { vacancy: v, onclick });

		const card = screen.getByRole("button");
		card.focus();
		await userEvent.setup().keyboard("{Enter}");
		expect(onclick).toHaveBeenCalledWith(v);
	});

	it("Space on a focused card triggers onclick", async () => {
		const onclick = vi.fn();
		const v = vacancy({ id: 5 });
		render(VacancyCard, { vacancy: v, onclick });

		const card = screen.getByRole("button");
		card.focus();
		await userEvent.setup().keyboard(" ");
		expect(onclick).toHaveBeenCalledWith(v);
	});

	it("other keys do not trigger onclick", async () => {
		const onclick = vi.fn();
		render(VacancyCard, { vacancy: vacancy(), onclick });

		const card = screen.getByRole("button");
		card.focus();
		await userEvent.setup().keyboard("a");
		expect(onclick).not.toHaveBeenCalled();
	});

	it("renders without an onclick handler (no throw)", () => {
		expect(() => render(VacancyCard, { vacancy: vacancy() })).not.toThrow();
	});
});
