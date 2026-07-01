/**
 * Viewmodel is a Svelte 5 class that uses `$derived` for its read-only
 * properties. In tests we drive it by:
 *
 *  - Constructing the viewmodel with a plain-object query stub (the .data /
 *    .isPending / .isError fields), a fake QueryClient, and a real
 *    LetterReviewStore (also runes-based, tested separately).
 *  - Reading the derived fields — they re-evaluate on each get.
 *
 * Reactivity across multiple mutations of the same stub is not observed
 * here (that would require $state on the stub itself). Each scenario
 * instantiates a fresh viewmodel with the specific fixture it needs.
 */

import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it } from "vitest";
import type {
	ApplicationDetail,
	CoverLetter,
	ProcessingState,
	Vacancy,
} from "$lib/api/types";
import { LetterReviewStore } from "$lib/stores/letter_review.svelte";
import { LetterReviewSheetViewModel } from "./letter-review-sheet.viewmodel.svelte";

interface QueryStub<T> {
	data: T | null | undefined;
	isPending: boolean;
	isError: boolean;
	error?: unknown;
}

function makeFakeQueryClient(vacancies: Vacancy[] = []): QueryClient {
	return {
		getQueryData: <T>(_key: unknown) => vacancies as unknown as T,
	} as unknown as QueryClient;
}

function detail(overrides: Partial<ApplicationDetail> = {}): ApplicationDetail {
	return {
		vacancy_id: 1,
		application_id: 100,
		retry_count: 0,
		status: "letter_ready",
		reason: null,
		created_at: "2026-07-01T10:00:00Z",
		updated_at: "2026-07-01T10:00:00Z",
		latest_letter: null,
		letters_count: 0,
		...overrides,
	};
}

function letter(overrides: Partial<CoverLetter> = {}): CoverLetter {
	return {
		text: "hello",
		version: 1,
		created_at: "2026-07-01T10:00:00Z",
		...overrides,
	};
}

function makeVM(
	appStub: QueryStub<ApplicationDetail>,
	{
		vacancies = [] as Vacancy[],
		vacancyId = 1 as number | null,
		historyStub = { data: [], isPending: false, isError: false } as QueryStub<
			CoverLetter[]
		>,
	} = {},
): LetterReviewSheetViewModel {
	const store = new LetterReviewStore();
	if (vacancyId !== null) store.open(vacancyId);
	return new LetterReviewSheetViewModel(
		makeFakeQueryClient(vacancies),
		store,
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		appStub as any,
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		historyStub as any,
	);
}

describe("LetterReviewSheetViewModel — isOpen", () => {
	it("is closed when the store has no vacancy", () => {
		const store = new LetterReviewStore();
		const vm = new LetterReviewSheetViewModel(
			makeFakeQueryClient(),
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			{ data: null, isPending: false, isError: false } as any,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			{ data: [], isPending: false, isError: false } as any,
		);
		expect(vm.isOpen).toBe(false);
	});

	it("is open when the store has a vacancy id", () => {
		const vm = makeVM({ data: null, isPending: false, isError: false });
		expect(vm.isOpen).toBe(true);
	});
});

describe("Review — derived state from ApplicationQuery", () => {
	it("status defaults to 'parsed' when no application yet", () => {
		const vm = makeVM({ data: null, isPending: false, isError: false });
		expect(vm.review.status).toBe<ProcessingState>("parsed");
		expect(vm.review.hasApplication).toBe(false);
	});

	it("mirrors the application status once loaded", () => {
		const vm = makeVM({
			data: detail({ status: "letter_ready" }),
			isPending: false,
			isError: false,
		});
		expect(vm.review.status).toBe<ProcessingState>("letter_ready");
		expect(vm.review.hasApplication).toBe(true);
	});

	it("isGenerating is true only in letter_pending", () => {
		const pending = makeVM({
			data: detail({ status: "letter_pending" }),
			isPending: false,
			isError: false,
		});
		expect(pending.review.isGenerating).toBe(true);

		const ready = makeVM({
			data: detail({ status: "letter_ready" }),
			isPending: false,
			isError: false,
		});
		expect(ready.review.isGenerating).toBe(false);
	});

	it("isSubmitting is true only in letter_sending", () => {
		const sending = makeVM({
			data: detail({ status: "letter_sending" }),
			isPending: false,
			isError: false,
		});
		expect(sending.review.isSubmitting).toBe(true);

		const sent = makeVM({
			data: detail({ status: "letter_sent" }),
			isPending: false,
			isError: false,
		});
		expect(sent.review.isSubmitting).toBe(false);
	});

	it("mirrors isPending/isError from the underlying query", () => {
		const loading = makeVM({
			data: undefined,
			isPending: true,
			isError: false,
		});
		expect(loading.review.isLoading).toBe(true);

		const errored = makeVM({
			data: undefined,
			isPending: false,
			isError: true,
			error: new Error("boom"),
		});
		expect(errored.review.isError).toBe(true);
	});

	it("exposes reason as `error`", () => {
		const vm = makeVM({
			data: detail({ status: "error", reason: "captcha" }),
			isPending: false,
			isError: false,
		});
		expect(vm.review.error).toBe("captcha");
	});

	it("looks up the vacancy in the QueryClient cache by id", () => {
		const cachedVacancy: Vacancy = {
			id: 1,
			title: "Dev",
			apply_link: "https://hh.ru/vacancy/1",
			description: "d",
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
		};
		const vm = makeVM(
			{ data: detail(), isPending: false, isError: false },
			{ vacancies: [cachedVacancy], vacancyId: 1 },
		);
		expect(vm.review.vacancy).toEqual(cachedVacancy);
	});

	it("returns null vacancy when the id is not in the cache", () => {
		const vm = makeVM(
			{ data: detail(), isPending: false, isError: false },
			{ vacancies: [], vacancyId: 42 },
		);
		expect(vm.review.vacancy).toBeNull();
	});
});

describe("LetterReviewSheetCoverLetter — editability", () => {
	it.each<[ProcessingState, boolean]>([
		["letter_ready", true],
		["letter_reviewing", true],
		["error", true],
		["letter_pending", false],
		["letter_sending", false],
		["letter_sent", false],
		["skipped", false],
		["parsed", false],
	])("isEditable for status=%s → %p", (status, expected) => {
		const vm = makeVM({
			data: detail({ status }),
			isPending: false,
			isError: false,
		});
		expect(vm.cover_letter.isEditable).toBe(expected);
	});

	// The Save button visibility MUST mirror isEditable — otherwise there
	// are states where the user can type but cannot persist their edits
	// (the exact regression reported on 2026-07-01: no Save button in ERROR
	// state after a failed submit).
	it.each<ProcessingState>([
		"parsed",
		"letter_pending",
		"letter_ready",
		"letter_reviewing",
		"letter_sending",
		"letter_sent",
		"error",
		"skipped",
	])(
		"showSaveButton === isEditable for status=%s (Save is always available when editable)",
		(status) => {
			const vm = makeVM({
				data: detail({ status }),
				isPending: false,
				isError: false,
			});
			expect(vm.cover_letter.showSaveButton).toBe(vm.cover_letter.isEditable);
		},
	);

	it("showSaveButton is true in the ERROR state (regression)", () => {
		const vm = makeVM({
			data: detail({ status: "error", reason: "network" }),
			isPending: false,
			isError: false,
		});
		expect(vm.cover_letter.showSaveButton).toBe(true);
	});

	it.each<[ProcessingState, boolean]>([
		["letter_sending", true],
		["letter_sent", true],
		["skipped", true],
		["letter_ready", false],
		["letter_pending", false],
		["error", false],
		["parsed", false],
	])("isReadOnly for status=%s → %p", (status, expected) => {
		const vm = makeVM({
			data: detail({ status }),
			isPending: false,
			isError: false,
		});
		expect(vm.cover_letter.isReadOnly).toBe(expected);
	});
});

describe("LetterReviewSheetCoverLetter — latest + isDirty", () => {
	it("latest is null when there is no letter", () => {
		const vm = makeVM({
			data: detail({ latest_letter: null }),
			isPending: false,
			isError: false,
		});
		expect(vm.cover_letter.latest).toBeNull();
		expect(vm.cover_letter.isDirty).toBe(false);
	});

	it("latest surfaces the letter from ApplicationDetail", () => {
		const l = letter({ text: "server text", version: 4 });
		const vm = makeVM({
			data: detail({ latest_letter: l }),
			isPending: false,
			isError: false,
		});
		expect(vm.cover_letter.latest).toEqual(l);
	});

	it("isDirty=false when localText matches the server letter text", () => {
		const l = letter({ text: "server text" });
		const vm = makeVM({
			data: detail({ latest_letter: l }),
			isPending: false,
			isError: false,
		});
		vm.cover_letter.localText = "server text";
		expect(vm.cover_letter.isDirty).toBe(false);
	});

	it("isDirty=true when localText diverges from the server letter", () => {
		const l = letter({ text: "server" });
		const vm = makeVM({
			data: detail({ latest_letter: l }),
			isPending: false,
			isError: false,
		});
		vm.cover_letter.localText = "edited";
		expect(vm.cover_letter.isDirty).toBe(true);
	});

	it("isDirty depends only on length when there is no server letter", () => {
		const vm = makeVM({
			data: detail({ latest_letter: null }),
			isPending: false,
			isError: false,
		});
		expect(vm.cover_letter.isDirty).toBe(false);
		vm.cover_letter.localText = "a";
		expect(vm.cover_letter.isDirty).toBe(true);
	});
});

describe("LetterReviewSheetViewModel — tab state", () => {
	it("defaults to the 'letter' tab", () => {
		const vm = makeVM({
			data: detail(),
			isPending: false,
			isError: false,
		});
		expect(vm.tab).toBe("letter");
	});

	it("can be flipped to 'history'", () => {
		const vm = makeVM({
			data: detail(),
			isPending: false,
			isError: false,
		});
		vm.tab = "history";
		expect(vm.tab).toBe("history");
	});
});
