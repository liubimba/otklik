import type {
	ApplicationDetail,
	CoverLetter,
	ProcessingState,
	Vacancy,
} from "$lib/api/types";
import { LetterReviewStore } from "$lib/stores/letter_review.svelte";
import type { QueryClient } from "@tanstack/svelte-query";
import { describe, expect, it } from "vitest";
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
		error_domain: null,
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
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		{ data: [], isPending: false, isError: false } as any,
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

describe("Chat — canChat gating", () => {
	it("allows chatting in the error state", () => {
		const vm = makeVM({
			data: detail({ status: "error" }),
			isPending: false,
			isError: false,
		});
		expect(vm.chat.canChat).toBe(true);
	});

	it("allows chatting while the letter is up for review", () => {
		for (const status of ["letter_ready", "letter_reviewing"] as const) {
			const vm = makeVM({
				data: detail({ status }),
				isPending: false,
				isError: false,
			});
			expect(vm.chat.canChat).toBe(true);
		}
	});

	it("blocks chatting in in-flight and terminal states", () => {
		for (const status of [
			"letter_pending",
			"letter_sending",
			"letter_sent",
			"skipped",
		] as const) {
			const vm = makeVM({
				data: detail({ status }),
				isPending: false,
				isError: false,
			});
			expect(vm.chat.canChat).toBe(false);
		}
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

	it.each<[ProcessingState, boolean]>([
		["letter_ready", true],
		["letter_reviewing", true],
		["error", true],
		["parsed", false],
		["letter_pending", false],
		["letter_sending", false],
		["letter_sent", false],
		["skipped", false],
	])("canSubmit for status=%s → %p", (status, expected) => {
		const vm = makeVM({
			data: detail({ status }),
			isPending: false,
			isError: false,
		});
		expect(vm.review.canSubmit).toBe(expected);
	});

	it("canSubmit is true in ERROR (regression: unified with letter_ready)", () => {
		const vm = makeVM({
			data: detail({ status: "error", reason: "captcha" }),
			isPending: false,
			isError: false,
		});
		expect(vm.review.canSubmit).toBe(true);
	});

	it.each<[ProcessingState, boolean]>([
		["letter_ready", true],
		["letter_reviewing", true],
		["error", true],
		["parsed", false],
		["letter_pending", false],
		["letter_sending", false],
		["letter_sent", false],
		["skipped", false],
	])("canRegenerate for status=%s → %p", (status, expected) => {
		const vm = makeVM({
			data: detail({ status }),
			isPending: false,
			isError: false,
		});
		expect(vm.review.canRegenerate).toBe(expected);
	});

	it("canRegenerate is true in ERROR (regression: matches the new backend arc)", () => {
		const vm = makeVM({
			data: detail({ status: "error", reason: "not authorized" }),
			isPending: false,
			isError: false,
		});
		expect(vm.review.canRegenerate).toBe(true);
	});

	describe("error explains provider failures in plain language", () => {
		it("explains a dead local model instead of showing the raw provider error", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "connection refused",
					error_domain: "model",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toContain("Ollama");
		});

		it("explains ECONNREFUSED the same way", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "ECONNREFUSED",
					error_domain: "model",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toContain("Ollama");
		});

		it("explains a rejected api key", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "401 invalid api key",
					error_domain: "model",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toContain("Настройках");
		});

		it("explains a timeout", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "Request timed out",
					error_domain: "model",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toContain("облачный ключ");
		});

		it("passes an unrecognized error through verbatim — no false confidence behind a generic phrase", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "database is locked",
					error_domain: "model",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toBe("database is locked");
		});

		it("stays null/undefined when there is no reason", () => {
			const vm = makeVM({
				data: detail({ status: "letter_ready", reason: null }),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toBeFalsy();
		});
	});

	describe("error — hh.ru submission failures are never explained as model failures", () => {
		it("shows a hh.ru verification-timeout reason verbatim, not the model-timeout hint", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "verification timeout",
					error_domain: "submission",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toBe("verification timeout");
			expect(vm.review.error).not.toContain("Модель");
			expect(vm.review.error).not.toContain("облачный ключ");
		});

		it("shows a hh.ru reason verbatim even when its text overlaps a model-error pattern", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "Timeout 30000ms exceeded",
					error_domain: "submission",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toBe("Timeout 30000ms exceeded");
		});

		it("shows the not-authorized submission reason verbatim", () => {
			const vm = makeVM({
				data: detail({
					status: "error",
					reason: "not authorized",
					error_domain: "submission",
				}),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toBe("not authorized");
		});

		it("does not translate a reason when error_domain is absent from an older cached payload", () => {
			const vm = makeVM({
				data: detail({ status: "error", reason: "connection refused" }),
				isPending: false,
				isError: false,
			});
			expect(vm.review.error).toBe("connection refused");
		});
	});

	it("looks up the vacancy in the QueryClient cache by id", () => {
		const cachedVacancy: Vacancy = {
			id: 1,
			title: "Dev",
			apply_link: "https://hh.ru/vacancy/1",
			description: "d",
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

describe("LetterReviewSheetCoverLetter — undo / redo", () => {
	function editable() {
		return makeVM({
			data: detail({ status: "letter_ready" }),
			isPending: false,
			isError: false,
		});
	}

	it("starts with empty history (canUndo=false, canRedo=false)", () => {
		const vm = editable();
		expect(vm.cover_letter.canUndo).toBe(false);
		expect(vm.cover_letter.canRedo).toBe(false);
	});

	it("setText pushes the previous value onto the undo stack", () => {
		const vm = editable();
		vm.cover_letter.setText("a");
		vm.cover_letter.setText("ab");
		expect(vm.cover_letter.canUndo).toBe(true);
		expect(vm.cover_letter.localText).toBe("ab");
	});

	it("setText with pushHistory=false does NOT record history", () => {
		const vm = editable();
		vm.cover_letter.setText("server text", { pushHistory: false });
		expect(vm.cover_letter.canUndo).toBe(false);
		expect(vm.cover_letter.localText).toBe("server text");
	});

	it("setText with identical value does not push a duplicate entry", () => {
		const vm = editable();
		vm.cover_letter.setText("same");
		vm.cover_letter.setText("same");
		vm.cover_letter.undo();
		expect(vm.cover_letter.canUndo).toBe(false);
	});

	it("undo restores the previous value and unlocks canRedo", () => {
		const vm = editable();
		vm.cover_letter.setText("a");
		vm.cover_letter.setText("ab");

		expect(vm.cover_letter.undo()).toBe(true);
		expect(vm.cover_letter.localText).toBe("a");
		expect(vm.cover_letter.canRedo).toBe(true);
	});

	it("undo returns false and is a no-op when the stack is empty", () => {
		const vm = editable();
		expect(vm.cover_letter.undo()).toBe(false);
		expect(vm.cover_letter.localText).toBe("");
	});

	it("multiple undos rewind through the whole history", () => {
		const vm = editable();
		vm.cover_letter.setText("a");
		vm.cover_letter.setText("ab");
		vm.cover_letter.setText("abc");

		vm.cover_letter.undo();
		vm.cover_letter.undo();
		vm.cover_letter.undo();
		expect(vm.cover_letter.localText).toBe("");
		expect(vm.cover_letter.canUndo).toBe(false);
		expect(vm.cover_letter.undo()).toBe(false);
	});

	it("redo re-applies the last undone value", () => {
		const vm = editable();
		vm.cover_letter.setText("hello");
		vm.cover_letter.undo();
		expect(vm.cover_letter.localText).toBe("");
		expect(vm.cover_letter.redo()).toBe(true);
		expect(vm.cover_letter.localText).toBe("hello");
	});

	it("redo returns false when the redo stack is empty", () => {
		const vm = editable();
		expect(vm.cover_letter.redo()).toBe(false);
	});

	it("a fresh edit after undo drops the redo stack", () => {
		const vm = editable();
		vm.cover_letter.setText("a");
		vm.cover_letter.setText("ab");
		vm.cover_letter.undo();
		expect(vm.cover_letter.canRedo).toBe(true);

		vm.cover_letter.setText("new branch");
		expect(vm.cover_letter.canRedo).toBe(false);
	});

	it("clearHistory wipes both stacks", () => {
		const vm = editable();
		vm.cover_letter.setText("a");
		vm.cover_letter.setText("b");
		vm.cover_letter.undo();

		vm.cover_letter.clearHistory();
		expect(vm.cover_letter.canUndo).toBe(false);
		expect(vm.cover_letter.canRedo).toBe(false);
	});

	it("caps undo history at MAX_HISTORY (drops the oldest entry)", () => {
		const vm = editable();
		for (let i = 0; i < 505; i++) {
			vm.cover_letter.setText(String(i));
		}
		while (vm.cover_letter.undo()) {}
		expect(vm.cover_letter.localText).not.toBe("");
		expect(vm.cover_letter.localText).toBe("4");
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
