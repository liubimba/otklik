import type { AICoverLetterResponse } from "$lib/api/types";
import { QueryClient } from "@tanstack/svelte-query";
import { render, screen, waitFor } from "@testing-library/svelte";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const stub = vi.hoisted(() => ({
	generate: {
		mutate: vi.fn(),
		isPending: false,
		isError: false,
		error: null as Error | null,
	},
}));

vi.mock("$lib/actions", () => ({
	createActions: () => ({
		preview: { generate: stub.generate },
	}),
}));

import { m } from "$lib/paraglide/messages";
import PlaygroundPageHarness from "./page-harness.svelte";

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return render(PlaygroundPageHarness, { props: { queryClient } });
}

beforeEach(() => {
	window.localStorage.clear();
	stub.generate.mutate.mockReset();
	stub.generate.isPending = false;
	stub.generate.isError = false;
	stub.generate.error = null;
});

describe("/playground — the test vacancy form", () => {
	it("renders prefilled with a plausible example vacancy", () => {
		renderPage();

		expect(screen.getByLabelText(m.playground_field_title())).toHaveValue(
			"Backend-разработчик (Python)",
		);
		const description = screen.getByLabelText(
			m.playground_field_description(),
		) as HTMLTextAreaElement;
		expect(description.value).not.toBe("");
	});

	it("calls the generate mutation with the current field values", async () => {
		const user = userEvent.setup();
		renderPage();

		const company = screen.getByLabelText(m.playground_field_company());
		await user.clear(company);
		await user.type(company, "Рога и Копыта");

		await user.click(
			screen.getByRole("button", { name: m.playground_generate() }),
		);

		expect(stub.generate.mutate).toHaveBeenCalledTimes(1);
		expect(stub.generate.mutate.mock.calls[0]?.[0]).toEqual({
			title: "Backend-разработчик (Python)",
			description: expect.stringContaining("FastAPI"),
			company_name: "Рога и Копыта",
			salary: "250 000 – 350 000 ₽ на руки",
			work_location: "Москва",
			work_experience: "От 3 до 6 лет",
		});
	});

	it("persists the field values to localStorage across a re-render", async () => {
		const user = userEvent.setup();
		renderPage();

		const salary = screen.getByLabelText(m.playground_field_salary());
		await user.clear(salary);
		await user.type(salary, "от 400 000 ₽");

		await waitFor(() => {
			const stored = window.localStorage.getItem("otklik:playground:form");
			expect(stored).toContain("от 400 000 ₽");
		});
	});

	it("disables the button and shows the pending label while a generation is in flight", () => {
		stub.generate.isPending = true;
		renderPage();

		expect(
			screen.getByRole("button", { name: m.playground_generate_pending() }),
		).toBeDisabled();
	});

	it("shows the error message when the mutation fails", () => {
		stub.generate.isError = true;
		stub.generate.error = new Error("model unavailable");
		renderPage();

		expect(
			screen.getByText(
				m.playground_generate_error({ error: "model unavailable" }),
			),
		).toBeInTheDocument();
	});
});

describe("/playground — the generated letter", () => {
	it("shows an empty state before the first generation", () => {
		renderPage();

		expect(screen.getByText(m.playground_result_empty())).toBeInTheDocument();
	});

	it("renders the letter text and meta info once generation succeeds", async () => {
		const user = userEvent.setup();
		let onSuccess: ((data: AICoverLetterResponse) => void) | undefined;
		stub.generate.mutate.mockImplementation(
			(_body: unknown, opts?: { onSuccess?: typeof onSuccess }) => {
				onSuccess = opts?.onSuccess;
			},
		);
		renderPage();

		await user.click(
			screen.getByRole("button", { name: m.playground_generate() }),
		);

		const response: AICoverLetterResponse = {
			text: "Уважаемый работодатель, откликаюсь на вакансию.",
			model_used: "openai/gpt-4o",
			prompt_tokens: 100,
			completion_tokens: 50,
			total_tokens: 150,
			was_fallback: true,
			cost_usd: 0.0123,
		};
		onSuccess?.(response);

		expect(
			await screen.findByDisplayValue(
				"Уважаемый работодатель, откликаюсь на вакансию.",
			),
		).toBeInTheDocument();
		expect(
			screen.getByText(m.playground_meta_model({ model: "openai/gpt-4o" })),
		).toBeInTheDocument();
		expect(
			screen.getByText(m.playground_meta_tokens({ tokens: 150 })),
		).toBeInTheDocument();
		expect(
			screen.getByText(m.playground_meta_cost({ cost: "$0.0123" })),
		).toBeInTheDocument();
		expect(screen.getByText(m.playground_meta_fallback())).toBeInTheDocument();
	});
});
