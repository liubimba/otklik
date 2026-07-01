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
	localText = $state("");
	lastSyncedVersion = $state<number | null>(null);
	restoreCandidate = $state<CoverLetter | null>(null);

	readonly latest: CoverLetter | null;
	readonly isEditable: boolean;
	readonly isReadOnly: boolean;
	readonly isDirty: boolean;

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

		this.isDirty = $derived(
			this.latest
				? this.localText !== this.latest.text
				: this.localText.length > 0,
		);
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
