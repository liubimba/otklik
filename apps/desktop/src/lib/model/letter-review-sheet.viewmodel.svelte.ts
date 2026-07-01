import type { CoverLetter, ProcessingState, Vacancy } from "$lib/api/types";
import type {
	createApplicationQuery,
	createCoverLettersHistoryQuery,
} from "$lib/queries/applications";
import { vacanciesQueryKey } from "$lib/queries/vacancies";
import type { LetterReviewStore } from "$lib/stores/letter_review.svelte";
import type { QueryClient } from "@tanstack/svelte-query";

type ApplicationQuery = ReturnType<typeof createApplicationQuery>;
type CoverLettersHistoryQuery = ReturnType<
	typeof createCoverLettersHistoryQuery
>;

export type Tab = "letter" | "history";

class Review {
	readonly status: ProcessingState;
	readonly hasApplication: boolean;
	readonly isLoading: boolean;
	readonly isError: boolean;
	readonly vacancy: Vacancy | null;
	readonly isGenerating: boolean;
	readonly isSubmitting: boolean;
	/**
	 * Whether the "Отправить" button should be shown in the footer. Mirrors
	 * the SUBMIT-event arcs on the backend state machine (letter_ready,
	 * letter_reviewing, error). ERROR was added on 2026-07-01 to let the
	 * user re-submit an existing letter after a transient failure without
	 * a forced LLM regeneration (which is what RETRY does).
	 */
	readonly canSubmit: boolean;
	/**
	 * Whether the "Сгенерировать заново" (Regenerate) button should be
	 * shown in the footer. Mirrors the LETTER_GENERATED-event arcs on the
	 * backend state machine that the UI actually surfaces —
	 * letter_ready / letter_reviewing / error. Excludes letter_pending
	 * (that IS a regeneration-in-progress; the footer shows a spinner
	 * instead) and PARSED (which has its own initial-generate button).
	 */
	readonly canRegenerate: boolean;
	readonly error;

	constructor(
		private readonly applicationStatus: ApplicationQuery,
		private readonly queryClient: QueryClient,
		private readonly store: LetterReviewStore,
	) {
		this.status = $derived(
			(this.applicationStatus.data?.status ?? "parsed") as ProcessingState,
		);

		this.hasApplication = $derived(
			this.applicationStatus.data !== null &&
				this.applicationStatus.data !== undefined,
		);

		this.isLoading = $derived(this.applicationStatus.isPending);

		this.isError = $derived(this.applicationStatus.isError);
		this.error = $derived(this.applicationStatus.data?.reason);

		this.isGenerating = $derived(this.status === "letter_pending");
		this.isSubmitting = $derived(this.status === "letter_sending");

		this.canSubmit = $derived(
			this.status === "letter_ready" ||
				this.status === "letter_reviewing" ||
				this.status === "error",
		);

		this.canRegenerate = $derived(
			this.status === "letter_ready" ||
				this.status === "letter_reviewing" ||
				this.status === "error",
		);

		this.vacancy = $derived.by((): Vacancy | null => {
			const id = this.store.vacancyId;
			if (id === null) return null;
			const cached =
				this.queryClient.getQueryData<Vacancy[]>(vacanciesQueryKey);
			return cached?.find((v) => v.id === id) ?? null;
		});
	}
}

class LetterReviewSheetCoverLetter {
	/**
	 * Upper bound on undo history size. Every keystroke pushes a snapshot,
	 * so a long editing session could otherwise grow unbounded. 500 covers
	 * a full-page rewrite without hitting the cap in practice.
	 */
	private static readonly MAX_HISTORY = 500;

	localText = $state("");
	lastSyncedVersion = $state<number | null>(null);
	restoreCandidate = $state<CoverLetter | null>(null);

	private undoStack = $state<string[]>([]);
	private redoStack = $state<string[]>([]);

	readonly latest: CoverLetter | null;
	readonly isEditable: boolean;
	readonly isReadOnly: boolean;
	/**
	 * Whether the Save button should be rendered in the footer. Mirrors
	 * `isEditable` on purpose — if the user can type into the textarea,
	 * they must have a way to persist the edit. Prior to 2026-07-01 the
	 * template gated Save on `status ∈ {letter_ready, letter_reviewing}`
	 * only, silently dropping the button in the ERROR state where the
	 * textarea is still editable (regression noted by the user).
	 */
	readonly showSaveButton: boolean;
	readonly isDirty: boolean;
	readonly canUndo: boolean;
	readonly canRedo: boolean;

	constructor(private readonly applicationStatus: ApplicationQuery) {
		this.latest = $derived(this.applicationStatus.data?.latest_letter ?? null);

		this.isEditable = $derived(
			this.applicationStatus.data?.status === "letter_ready" ||
				this.applicationStatus.data?.status === "letter_reviewing" ||
				this.applicationStatus.data?.status === "error",
		);

		this.isReadOnly = $derived(
			this.applicationStatus.data?.status === "letter_sending" ||
				this.applicationStatus.data?.status === "letter_sent" ||
				this.applicationStatus.data?.status === "skipped",
		);

		this.showSaveButton = $derived(this.isEditable);

		this.isDirty = $derived(
			this.latest
				? this.localText !== this.latest.text
				: this.localText.length > 0,
		);

		this.canUndo = $derived(this.undoStack.length > 0);
		this.canRedo = $derived(this.redoStack.length > 0);
	}

	/**
	 * Single source of truth for changes to `localText`. Every edit records
	 * the previous value on the undo stack and drops the redo stack (any
	 * fresh edit invalidates the redo timeline). Server-driven syncs pass
	 * `pushHistory: false` and pair the call with `clearHistory()` — Ctrl+Z
	 * must not step past a version-boundary imposed by the server.
	 */
	setText(next: string, opts: { pushHistory?: boolean } = {}): void {
		const pushHistory = opts.pushHistory ?? true;
		if (pushHistory && this.localText !== next) {
			this.undoStack.push(this.localText);
			if (this.undoStack.length > LetterReviewSheetCoverLetter.MAX_HISTORY) {
				this.undoStack.shift();
			}
			this.redoStack = [];
		}
		this.localText = next;
	}

	/** Pop one snapshot off the undo stack and make it the current value. */
	undo(): boolean {
		const prev = this.undoStack.pop();
		if (prev === undefined) return false;
		this.redoStack.push(this.localText);
		this.localText = prev;
		return true;
	}

	/** Reverse of undo(): pop the redo stack and re-apply. */
	redo(): boolean {
		const next = this.redoStack.pop();
		if (next === undefined) return false;
		this.undoStack.push(this.localText);
		this.localText = next;
		return true;
	}

	clearHistory(): void {
		this.undoStack = [];
		this.redoStack = [];
	}
}

export class LetterReviewSheetViewModel {
	readonly review: Review;
	readonly cover_letter: LetterReviewSheetCoverLetter;
	readonly isOpen: boolean;

	tab = $state<Tab>("letter");

	constructor(
		private readonly queryClient: QueryClient,
		private readonly store: LetterReviewStore,
		public readonly applicationStatus: ApplicationQuery,
		public readonly coverLettersHistory: CoverLettersHistoryQuery,
	) {
		this.review = new Review(applicationStatus, queryClient, store);
		this.cover_letter = new LetterReviewSheetCoverLetter(applicationStatus);
		this.isOpen = $derived(this.store.vacancyId !== null);
	}
}

export const createLetterReviewSheetViewModel = (
	queryClient: QueryClient,
	store: LetterReviewStore,
	applicationStatus: ApplicationQuery,
	coverLettersHistory: CoverLettersHistoryQuery,
) =>
	new LetterReviewSheetViewModel(
		queryClient,
		store,
		applicationStatus,
		coverLettersHistory,
	);
