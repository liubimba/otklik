import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CoverLetter } from "$lib/api/types";
import { LetterReviewStore } from "$lib/stores/letter_review.svelte";

vi.mock("svelte-sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

vi.mock("$lib/paraglide/messages", () => ({
	m: new Proxy(
		{},
		{
			get: (_target, prop) =>
				typeof prop === "string" ? () => `m:${prop}` : undefined,
		},
	),
}));

const { createLetterReviewSheetView } = await import(
	"./letter-review-sheet.view.svelte"
);

/**
 * Minimal test doubles for the two collaborators the view depends on.
 * We intentionally do NOT spin up a real query client + mutations — this
 * suite is about the view's own control flow (guards, wiring, no-ops).
 */
function makeActions() {
	const mutations = {
		generate: { mutateAsync: vi.fn(async () => ({})) },
		save: { mutateAsync: vi.fn(async () => ({})) },
		submit: { mutateAsync: vi.fn(async () => ({})) },
		skip: { mutateAsync: vi.fn(async () => ({})) },
		retry: { mutateAsync: vi.fn(async () => ({})) },
	};
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	return { letter: { review: mutations } } as any;
}

interface CoverLetterVM {
	localText: string;
	isDirty: boolean;
	isEditable: boolean;
	restoreCandidate: CoverLetter | null;
	setText: ReturnType<typeof vi.fn>;
	undo: ReturnType<typeof vi.fn>;
	redo: ReturnType<typeof vi.fn>;
}

function makeVM(
	overrides: Partial<CoverLetterVM> = {},
): { cover_letter: CoverLetterVM; tab: string } {
	return {
		tab: "letter",
		cover_letter: {
			localText: "",
			isDirty: false,
			isEditable: false,
			restoreCandidate: null,
			setText: vi.fn(),
			undo: vi.fn(),
			redo: vi.fn(),
			...overrides,
		},
	};
}

let store: LetterReviewStore;
beforeEach(() => {
	store = new LetterReviewStore();
});

describe("view.close — regression: no auto-save", () => {
	it("does NOT call save() even when the buffer is dirty and editable", async () => {
		const actions = makeActions();
		const vm = makeVM({ localText: "unsaved", isDirty: true, isEditable: true });
		store.open(1);
		const view = createLetterReviewSheetView(
			actions,
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			vm as any,
		);

		await view.close();
		expect(actions.letter.review.save.mutateAsync).not.toHaveBeenCalled();
		expect(store.vacancyId).toBeNull();
	});

	it("closes the store synchronously — no pending network call to await", async () => {
		const view = createLetterReviewSheetView(
			makeActions(),
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			makeVM() as any,
		);
		store.open(5);
		view.close();
		expect(store.vacancyId).toBeNull();
	});
});

describe("view.submit — dirty text is forwarded (atomic dirty-submit)", () => {
	it("forwards localText via submit when the buffer is dirty", async () => {
		const actions = makeActions();
		const vm = makeVM({ localText: "final draft", isDirty: true });
		store.open(9);
		const view = createLetterReviewSheetView(
			actions,
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			vm as any,
		);

		await view.submit();
		expect(actions.letter.review.submit.mutateAsync).toHaveBeenCalledWith({
			vacancyId: 9,
			text: "final draft",
		});
	});

	it("omits text when the buffer is clean (server uses existing letter)", async () => {
		const actions = makeActions();
		store.open(9);
		const view = createLetterReviewSheetView(
			actions,
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			makeVM({ localText: "server text", isDirty: false }) as any,
		);

		await view.submit();
		expect(actions.letter.review.submit.mutateAsync).toHaveBeenCalledWith({
			vacancyId: 9,
			text: undefined,
		});
	});
});

describe("view.confirmRestore — routes through setText for undo history", () => {
	it("assigns via cover_letter.setText() (not direct .localText =)", () => {
		const vm = makeVM({
			restoreCandidate: {
				text: "v3 text",
				version: 3,
				created_at: "x",
			},
		});
		store.open(1);
		const view = createLetterReviewSheetView(
			makeActions(),
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			vm as any,
		);

		view.confirmRestore();

		expect(vm.cover_letter.setText).toHaveBeenCalledWith("v3 text");
		expect(vm.cover_letter.restoreCandidate).toBeNull();
	});

	it("is a no-op when there is no restore candidate", () => {
		const vm = makeVM({ restoreCandidate: null });
		const view = createLetterReviewSheetView(
			makeActions(),
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			vm as any,
		);

		view.confirmRestore();
		expect(vm.cover_letter.setText).not.toHaveBeenCalled();
	});
});

describe("view.undo / view.redo — delegate to viewmodel", () => {
	it("undo() calls cover_letter.undo()", () => {
		const vm = makeVM();
		const view = createLetterReviewSheetView(
			makeActions(),
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			vm as any,
		);
		view.undo();
		expect(vm.cover_letter.undo).toHaveBeenCalledTimes(1);
	});

	it("redo() calls cover_letter.redo()", () => {
		const vm = makeVM();
		const view = createLetterReviewSheetView(
			makeActions(),
			store,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			vm as any,
		);
		view.redo();
		expect(vm.cover_letter.redo).toHaveBeenCalledTimes(1);
	});
});
