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
			await actions.letter.review.generate.mutateAsync(id);
			toast.success(m.review_generate_success());
		} catch (e) {
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
			toast.error(m.review_retry_failed({ error: errText(e) }));
		}
	}

	function close() {
		store.close();
	}

	function startRestore(version: CoverLetter) {
		vm.cover_letter.restoreCandidate = version;
	}

	function confirmRestore() {
		const candidate = vm.cover_letter.restoreCandidate;
		if (candidate === null) return;
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
					if (!letterStarted) {
						vm.cover_letter.streamReset();
						letterStarted = true;
					}
					vm.cover_letter.streamAppend(event.delta);
				} else if (event.type === "done") {
					appendChatTurn(id, message, vm.chat.streamingReply, event.version);
					queryClient.invalidateQueries({
						queryKey: applicationQueryKey(id),
					});
					queryClient.invalidateQueries({
						queryKey: coverLettersHistoryQueryKey(id),
					});
				} else if (event.type === "error") {
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
