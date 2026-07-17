import type {
	ChatMessage,
	CoverLetter,
	ProcessingState,
	Vacancy,
} from "$lib/api/types";
import type {
	createApplicationQuery,
	createChatMessagesQuery,
	createCoverLettersHistoryQuery,
} from "$lib/queries/applications";
import type { createVacancyQuery } from "$lib/queries/vacancies";
import { vacanciesQueryKey } from "$lib/queries/vacancies";
import type { LetterReviewStore } from "$lib/stores/letter_review.svelte";
import type { QueryClient } from "@tanstack/svelte-query";
import { explainProviderError } from "./provider-error";

type ApplicationQuery = ReturnType<typeof createApplicationQuery>;
type VacancyQuery = ReturnType<typeof createVacancyQuery>;
type CoverLettersHistoryQuery = ReturnType<
	typeof createCoverLettersHistoryQuery
>;
type ChatMessagesQuery = ReturnType<typeof createChatMessagesQuery>;

export type Tab = "letter" | "history";

class Review {
	readonly status: ProcessingState;
	readonly hasApplication: boolean;
	readonly isLoading: boolean;
	readonly isError: boolean;
	readonly vacancy: Vacancy | null;
	readonly isGenerating: boolean;
	readonly isSubmitting: boolean;
	readonly canSubmit: boolean;
	readonly canRegenerate: boolean;
	readonly error;

	constructor(
		private readonly applicationStatus: ApplicationQuery,
		private readonly queryClient: QueryClient,
		private readonly store: LetterReviewStore,
		private readonly vacancyQuery?: VacancyQuery,
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
		this.error = $derived.by(() => {
			const reason = this.applicationStatus.data?.reason;
			if (!reason) return reason;
			return this.applicationStatus.data?.error_domain === "model"
				? explainProviderError(reason)
				: reason;
		});

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
			const fetched = this.vacancyQuery?.data;
			if (fetched) return fetched;
			const cached =
				this.queryClient.getQueryData<Vacancy[]>(vacanciesQueryKey);
			return cached?.find((v) => v.id === id) ?? null;
		});
	}
}

class LetterReviewSheetCoverLetter {
	private static readonly MAX_HISTORY = 500;

	localText = $state("");
	lastSyncedVersion = $state<number | null>(null);
	restoreCandidate = $state<CoverLetter | null>(null);

	private undoStack = $state<string[]>([]);
	private redoStack = $state<string[]>([]);

	readonly latest: CoverLetter | null;
	readonly isEditable: boolean;
	readonly isReadOnly: boolean;
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

	undo(): boolean {
		const prev = this.undoStack.pop();
		if (prev === undefined) return false;
		this.redoStack.push(this.localText);
		this.localText = prev;
		return true;
	}

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

	streamReset(): void {
		this.localText = "";
	}

	streamAppend(delta: string): void {
		this.localText += delta;
	}
}

class Chat {
	input = $state("");
	isStreaming = $state(false);
	streamingReply = $state("");
	pendingUser = $state<string | null>(null);

	readonly messages: ChatMessage[];
	readonly canChat: boolean;

	constructor(
		private readonly chatQuery: ChatMessagesQuery,
		private readonly review: Review,
	) {
		this.messages = $derived(this.chatQuery.data ?? []);
		this.canChat = $derived(
			(this.review.status === "letter_ready" ||
				this.review.status === "letter_reviewing" ||
				this.review.status === "error") &&
				!this.isStreaming,
		);
	}

	begin(message: string): void {
		this.pendingUser = message;
		this.streamingReply = "";
		this.isStreaming = true;
		this.input = "";
	}

	appendReply(delta: string): void {
		this.streamingReply += delta;
	}

	reset(): void {
		this.isStreaming = false;
		this.pendingUser = null;
		this.streamingReply = "";
	}
}

export class LetterReviewSheetViewModel {
	readonly review: Review;
	readonly cover_letter: LetterReviewSheetCoverLetter;
	readonly chat: Chat;
	readonly isOpen: boolean;

	tab = $state<Tab>("letter");

	constructor(
		private readonly queryClient: QueryClient,
		private readonly store: LetterReviewStore,
		public readonly applicationStatus: ApplicationQuery,
		public readonly coverLettersHistory: CoverLettersHistoryQuery,
		public readonly chatMessages: ChatMessagesQuery,
		public readonly vacancyQuery?: VacancyQuery,
	) {
		this.review = new Review(
			applicationStatus,
			queryClient,
			store,
			vacancyQuery,
		);
		this.cover_letter = new LetterReviewSheetCoverLetter(applicationStatus);
		this.chat = new Chat(chatMessages, this.review);
		this.isOpen = $derived(this.store.vacancyId !== null);
	}
}

export const createLetterReviewSheetViewModel = (
	queryClient: QueryClient,
	store: LetterReviewStore,
	applicationStatus: ApplicationQuery,
	coverLettersHistory: CoverLettersHistoryQuery,
	chatMessages: ChatMessagesQuery,
	vacancyQuery?: VacancyQuery,
) =>
	new LetterReviewSheetViewModel(
		queryClient,
		store,
		applicationStatus,
		coverLettersHistory,
		chatMessages,
		vacancyQuery,
	);
