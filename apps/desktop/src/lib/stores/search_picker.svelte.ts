import {
	cancelFilterSession,
	confirmFilterSession,
	startFilterSession,
	startSearchVacancies,
} from "$lib/api/client";
import { APIError } from "$lib/api/error";
import type { SearchData } from "$lib/api/types";

type SearchPickerState =
	| { status: "idle" }
	| { status: "opening_session" }
	| { status: "awaiting_confirm"; session_id: string }
	| { status: "confirming"; session_id: string }
	| { status: "starting_search"; session_id: string }
	| { status: "canceling"; session_id: string }
	| { status: "error"; message: string };

function errorMessage(e: unknown): string {
	return e instanceof APIError ? e.detail : "Unknown error";
}

class SearchPickerStore {
	private _state = $state<SearchPickerState>({ status: "idle" });

	get state(): SearchPickerState {
		return this._state;
	}

	async startNewSession(): Promise<void> {
		if (this._state.status !== "idle" && this._state.status !== "error") {
			throw new Error(`startNewSession: invalid state ${this._state.status}`);
		}
		this._state = { status: "opening_session" };
		try {
			const { session_id } = await startFilterSession();
			this._state = { status: "awaiting_confirm", session_id };
		} catch (e) {
			this._state = { status: "error", message: errorMessage(e) };
		}
	}

	async confirmSession(
		max_pages?: number | null,
		max_vacancies?: number | null,
	): Promise<SearchData | null> {
		if (this._state.status !== "awaiting_confirm") {
			throw new Error(`confirmSession: invalid state ${this._state.status}`);
		}
		const session_id = this._state.session_id;
		this._state = { status: "confirming", session_id };
		try {
			const { url } = await confirmFilterSession(session_id);
			this._state = { status: "starting_search", session_id };
			const search = await startSearchVacancies(url, max_pages, max_vacancies);
			this._state = { status: "idle" };
			return search;
		} catch (e) {
			this._state = { status: "error", message: errorMessage(e) };
			return null;
		}
	}

	async cancelSession(): Promise<void> {
		if (this._state.status !== "awaiting_confirm") {
			throw new Error(`cancelSession: invalid state ${this._state.status}`);
		}
		const session_id = this._state.session_id;
		this._state = { status: "canceling", session_id };
		try {
			await cancelFilterSession(session_id);
			this._state = { status: "idle" };
		} catch (e) {
			this._state = { status: "error", message: errorMessage(e) };
		}
	}

	clearError(): void {
		if (this._state.status !== "error") return;
		this._state = { status: "idle" };
	}
}

export const searchPicker = new SearchPickerStore();
