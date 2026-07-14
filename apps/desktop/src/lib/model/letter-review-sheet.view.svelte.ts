import type { createActions } from "$lib/actions";
import { API } from "$lib/api/client";
import type { ChatMessage, CoverLetter } from "$lib/api/types";
import { m } from "$lib/paraglide/messages";
import {
	applicationQueryKey,
	chatMessagesQueryKey,
	coverLettersHistoryQueryKey,
} from "$lib/queries/applications";
import type { LetterReviewStore } from "$lib/stores/letter_review.svelte";
import type { QueryClient } from "@tanstack/svelte-query";
import { toast } from "svelte-sonner";
import type {
	LetterReviewSheetViewModel,
	Tab,
} from "./letter-review-sheet.viewmodel.svelte";
import { explainProviderError } from "./provider-error";

type Actions = ReturnType<typeof createActions>;

function errMsg(e: unknown): string {
	return e instanceof Error ? e.message : "unknown";
}

// Every mutation here surfaces whatever the backend threw, which — since the
// pre-generation model ping was removed (Task 2) — can be the raw provider
// error (`connection refused`, `401`, `timeout`). Route it through the same
// translator the letter review error banner uses so a toast reads as a
// sentence with a next step, not a stack-trace fragment.
function errText(e: unknown): string {
	return explainProviderError(errMsg(e));
}

export function createLetterReviewSheetView(
	queryClient: QueryClient,
	actions: Actions,
	store: LetterReviewStore,
	vm: LetterReviewSheetViewModel,
) {
	async function generate() {
		const id = store.vacancyId;
		if (id === null) return;
		try {
			// Server auto-creates the Application if none exists — no separate
			// queue_for_letter call required.
			await actions.letter.review.generate.mutateAsync(id);
			toast.success(m.review_generate_success());
		} catch (e) {
			// generate() also backs the footer's "Regenerate" button, so this
			// covers both the initial generation and regeneration paths — both
			// go straight to the AI layer, so their errors are provider errors.
			toast.error(m.review_generate_failed({ error: errText(e) }));
		}
	}

	async function save() {
		const id = store.vacancyId;
		if (id === null) return;
		try {
			await actions.letter.review.save.mutateAsync({
				vacancyId: id,
				text: vm.cover_letter.localText,
			});
			toast.success(m.review_save_success());
		} catch (e) {
			toast.error(m.review_save_failed({ error: errMsg(e) }));
		}
	}

	async function submit() {
		const id = store.vacancyId;
		if (id === null) return;
		// Atomic dirty-submit: send the current text along with SUBMIT so the
		// server saves + transitions in one round-trip.
		const text = vm.cover_letter.isDirty
			? vm.cover_letter.localText
			: undefined;
		try {
			await actions.letter.review.submit.mutateAsync({
				vacancyId: id,
				text,
			});
			toast.success(m.review_submit_success());
		} catch (e) {
			toast.error(m.review_submit_failed({ error: errMsg(e) }));
		}
	}

	async function skip() {
		const id = store.vacancyId;
		if (id === null) return;
		try {
			await actions.letter.review.skip.mutateAsync(id);
		} catch (e) {
			toast.error(m.review_skip_failed({ error: errMsg(e) }));
		}
	}

	async function retry() {
		const id = store.vacancyId;
		if (id === null) return;
		try {
			await actions.letter.review.retry.mutateAsync(id);
		} catch (e) {
			// RETRY resumes ERROR by re-running LLM generation on the backend
			// (ApplicationEvent.RETRY → LETTER_PENDING), so this is a provider
			// error too — unlike submit/skip, which stay in the hh.ru domain.
			toast.error(m.review_retry_failed({ error: errText(e) }));
		}
	}

	// Close discards unsaved edits by design. Prior behaviour auto-saved
	// on every close (removed on user's request 2026-07-01) surprised
	// users into persisting drafts they intended to throw away — a Sheet
	// close is a dismissal, not a commit.
	function close() {
		store.close();
	}

	function startRestore(version: CoverLetter) {
		vm.cover_letter.restoreCandidate = version;
	}

	function confirmRestore() {
		const candidate = vm.cover_letter.restoreCandidate;
		if (candidate === null) return;
		// Route through setText() so the pre-restore text lands on the undo
		// stack — Ctrl+Z after a restore takes the user back to what they
		// had, matching every other editor.
		vm.cover_letter.setText(candidate.text);
		vm.tab = "letter";
		vm.cover_letter.restoreCandidate = null;
	}

	function undo() {
		vm.cover_letter.undo();
	}

	function redo() {
		vm.cover_letter.redo();
	}

	function cancelRestore() {
		vm.cover_letter.restoreCandidate = null;
	}

	function setTab(tab: Tab) {
		vm.tab = tab;
	}

	/**
	 * Append the finished conversation turn straight into the chat query cache
	 * so the bubbles never flicker between clearing the optimistic in-flight
	 * pair and a refetch landing. Temporary client ids are fine for the
	 * session; the real persisted transcript is loaded on the next sheet open.
	 */
	function appendChatTurn(
		vacancyId: number,
		userText: string,
		assistantText: string,
		producedVersion: number | null,
	) {
		const now = new Date().toISOString();
		const base = Date.now();
		const turn: ChatMessage[] = [
			{
				id: base,
				role: "user",
				content: userText,
				produced_version: null,
				created_at: now,
			},
			{
				id: base + 1,
				role: "assistant",
				content: assistantText,
				produced_version: producedVersion,
				created_at: now,
			},
		];
		queryClient.setQueryData<ChatMessage[]>(
			chatMessagesQueryKey(vacancyId),
			(old) => [...(old ?? []), ...turn],
		);
	}

	async function sendChat() {
		const id = store.vacancyId;
		if (id === null) return;
		const message = vm.chat.input.trim();
		if (message === "" || vm.chat.isStreaming) return;

		vm.chat.begin(message);
		let letterStarted = false;
		try {
			for await (const event of API.application.chat.stream(id, message)) {
				if (event.type === "reply") {
					vm.chat.appendReply(event.delta);
				} else if (event.type === "letter") {
					// The model streams the FULL revised letter, so reset the
					// editor buffer on the first delta, then append.
					if (!letterStarted) {
						vm.cover_letter.streamReset();
						letterStarted = true;
					}
					vm.cover_letter.streamAppend(event.delta);
				} else if (event.type === "done") {
					appendChatTurn(id, message, vm.chat.streamingReply, event.version);
					// Pull the canonical letter/version + history; the editor
					// buffer-sync effect re-seeds from the new latest_letter.
					queryClient.invalidateQueries({
						queryKey: applicationQueryKey(id),
					});
					queryClient.invalidateQueries({
						queryKey: coverLettersHistoryQueryKey(id),
					});
				} else if (event.type === "error") {
					// Chat edits call the AI layer just like generate/retry, so
					// `event.detail` can be the same raw provider error.
					toast.error(explainProviderError(event.detail));
				}
			}
		} catch (e) {
			toast.error(m.review_chat_failed({ error: errText(e) }));
		} finally {
			vm.chat.reset();
		}
	}

	return {
		generate,
		save,
		submit,
		skip,
		retry,
		close,
		startRestore,
		confirmRestore,
		cancelRestore,
		setTab,
		undo,
		redo,
		sendChat,
		errMsg,
	};
}
