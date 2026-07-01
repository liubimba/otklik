import type { createActions } from "$lib/actions";
import type { CoverLetter } from "$lib/api/types";
import { m } from "$lib/paraglide/messages";
import type { LetterReviewStore } from "$lib/stores/letter_review.svelte";
import { toast } from "svelte-sonner";
import type {
	LetterReviewSheetViewModel,
	Tab,
} from "./letter-review-sheet.viewmodel.svelte";

type Actions = ReturnType<typeof createActions>;

function errMsg(e: unknown): string {
	return e instanceof Error ? e.message : "unknown";
}

export function createLetterReviewSheetView(
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
			toast.error(m.review_generate_failed({ error: errMsg(e) }));
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
			toast.error(m.review_retry_failed({ error: errMsg(e) }));
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
		errMsg,
	};
}
