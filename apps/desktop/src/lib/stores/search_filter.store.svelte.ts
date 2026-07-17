export type SearchFilterState =
	| { status: "idle" }
	| { status: "opening_session" }
	| { status: "awaiting_confirm"; session_id: string }
	| { status: "confirming"; session_id: string }
	| { status: "starting_search"; session_id: string }
	| { status: "canceling"; session_id: string }
	| { status: "error"; message?: string };

export class SearchFilterStore {
	private _state = $state<SearchFilterState>({
		status: "idle",
	});

	public get state(): SearchFilterState {
		return this._state;
	}

	public get sessionId(): string | null {
		switch (this._state.status) {
			case "awaiting_confirm":
			case "confirming":
			case "starting_search":
			case "canceling":
				return this._state.session_id;
			default:
				return null;
		}
	}

	public get canOpen(): boolean {
		return this._state.status === "idle" || this._state.status === "error";
	}

	public get canConfirm(): boolean {
		return this._state.status === "awaiting_confirm";
	}

	public get canCancel(): boolean {
		return (
			this._state.status === "awaiting_confirm" ||
			this._state.status === "confirming" ||
			this._state.status === "starting_search"
		);
	}

	public get isBusy(): boolean {
		return (
			this._state.status === "opening_session" ||
			this._state.status === "confirming" ||
			this._state.status === "starting_search" ||
			this._state.status === "canceling"
		);
	}

	public opening(): void {
		if (!this.canOpen) {
			throw new Error(`Cannot open from state '${this._state.status}'`);
		}

		this._state = {
			status: "opening_session",
		};
	}

	public opened(sessionId: string): void {
		if (this._state.status !== "opening_session") {
			throw new Error(
				`Cannot transition to awaiting_confirm from '${this._state.status}'`,
			);
		}

		this._state = {
			status: "awaiting_confirm",
			session_id: sessionId,
		};
	}

	public confirming(): void {
		if (this._state.status !== "awaiting_confirm") {
			throw new Error(`Cannot confirm from '${this._state.status}'`);
		}

		this._state = {
			status: "confirming",
			session_id: this._state.session_id,
		};
	}

	public confirmed(): void {
		if (this._state.status !== "confirming") {
			throw new Error(`Cannot complete search from '${this._state.status}'`);
		}

		this._state = {
			status: "idle",
		};
	}

	public searchStarted(): void {
		if (this._state.status !== "confirming") {
			throw new Error(`Cannot start search from '${this._state.status}'`);
		}

		this._state = {
			status: "starting_search",
			session_id: this._state.session_id,
		};
	}

	public canceling(): void {
		switch (this._state.status) {
			case "awaiting_confirm":
			case "confirming":
			case "starting_search":
				this._state = {
					status: "canceling",
					session_id: this._state.session_id,
				};
				return;

			default:
				throw new Error(`Cannot cancel from '${this._state.status}'`);
		}
	}

	public canceled(): void {
		if (this._state.status !== "canceling") {
			throw new Error(`Cannot finish cancel from '${this._state.status}'`);
		}

		this._state = {
			status: "idle",
		};
	}

	public failed(error?: string): void {
		this._state = {
			status: "error",
			message: error,
		};
	}

	public clearError(): void {
		if (this._state.status !== "error") {
			return;
		}

		this._state = {
			status: "idle",
		};
	}

	public reset(): void {
		this._state = {
			status: "idle",
		};
	}
}

export const searchFilterStateStore = new SearchFilterStore();
