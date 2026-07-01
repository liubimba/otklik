import {API} from "$lib/api/client";
import type {AuthEvent, AuthStatus} from "$lib/api/types";
import {getLogger} from "$lib/log";

export type AuthState =
    | { status: "authorizing" }
    | { status: "authorized" }
    | { status: "unauthorized" }
    | { status: "unknown" }
    | { status: "failed", reason: string }

export class AuthStore {
    private _state = $state<AuthState>({status: "unknown"});

    public get state(): AuthState {
        return this._state;
    }

    public get canAuthorize(): boolean {
        return this._state.status === "unauthorized" || this._state.status === "unknown";
    }

    public get canCancel(): boolean {
        return this._state.status === "authorizing";
    }

    public authorizing(): void {
        if (!this.canAuthorize) {
            this.throwInvalidState("authorizing");
        }
        this._state.status = "authorizing";
    }

    public authorized(): void {

        this._state.status = "authorized";
    }

    public unauthorized(): void {
        this._state.status = "unauthorized";
    }

    public clear(): void {
        this._state.status = "unknown";
    }

    public cancel(): void {
        if (!this.canCancel) {
            this.throwInvalidState("unknown");
        }
        this._state.status = "unknown";
    }

    public failed(reason: string): void {
        this._state = {
            status: "failed",
            reason: reason,
        }
    }

    private throwInvalidState(to: string) {
        throw new Error(`Cannot be transited to "${to}", invalid state: "${this._state.status}"`)
    }
}

export const authStore = new AuthStore();

function createAuthStore() {
    let state = $state<AuthStatus | null>(null);
    const logger = getLogger("AuthStore");

    async function fetchStatus() {
        logger.info("Fetching authentication status");
        try {
            state = await API.auth.status();
        } catch (error) {
            logger.error("Failed to fetch auth status:", error);
            state = null;
        }
    }

    async function fetchAuthentication() {
        if (state?.status === "authorizing") {
            logger.warn(
                "Already in the process of authorizing. Skipping new authentication attempt.",
            );
            return;
        }
        logger.info("Starting authentication process");
        try {
            state = await API.auth.signIn();
        } catch (error) {
            logger.error("Authentication failed:", error);
            state = null;
        }
    }

    function applyAuthEvent(event: AuthEvent) {
        logger.info(`Received auth status change event: ${event.data.status}`);
        state = event.data;
    }

    return {
        getState: () => state,
        fetchStatus,
        fetchAuthentication,
        applyAuthEvent,
    };
}

export const auth = createAuthStore();
