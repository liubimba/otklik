import { query } from "$lib/queries";
import { connection } from "$lib/stores/connection.svelte";
import { QueryClient } from "@tanstack/svelte-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createEventSync } from "./event-sync";
import type { ApplicationEvent, AuthEvent } from "./types";

function client(): QueryClient {
	return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

beforeEach(() => {
	connection.online();
});

describe("createEventSync", () => {
	describe("onConnect — resync on (re)connect", () => {
		it("marks the connection online", () => {
			const qc = client();
			connection.offline();
			createEventSync(qc).onConnect();
			expect(connection.isOnline).toBe(true);
			expect(connection.isOffline).toBe(false);
		});

		it("invalidates BOTH auth and summary — auth resync is what unsticks the profile skeleton when the backend starts after the app (bug #1)", () => {
			const qc = client();
			const invalidate = vi.spyOn(qc, "invalidateQueries");
			createEventSync(qc).onConnect();

			const keys = invalidate.mock.calls.map((c) =>
				JSON.stringify(c[0]?.queryKey),
			);
			expect(keys).toContain(JSON.stringify(query.auth.key));
			expect(keys).toContain(JSON.stringify(query.summary.key));
		});
	});

	describe("onDisconnect", () => {
		it("marks the connection offline (drives the banner + hides badges)", () => {
			const qc = client();
			connection.online();
			createEventSync(qc).onDisconnect();
			expect(connection.isOffline).toBe(true);
		});
	});

	describe("onEvent — cache mutations preserved after the extraction", () => {
		it("auth_changed writes the new status straight into the auth cache", () => {
			const qc = client();
			const set = vi.spyOn(qc, "setQueryData");
			const event: AuthEvent = {
				type: "auth_changed",
				data: { status: "authorized" },
			};
			createEventSync(qc).onEvent(event);
			expect(set).toHaveBeenCalledWith(query.auth.key, event.data);
		});

		it("application_event invalidates summary and the archive list", () => {
			const qc = client();
			const invalidate = vi.spyOn(qc, "invalidateQueries");
			const event: ApplicationEvent = {
				type: "application_event",
				data: {
					vacancy_id: 1,
					application_id: 1,
					status: "letter_ready",
					reason: null,
					error_domain: null,
				},
			};
			createEventSync(qc).onEvent(event);
			const keys = invalidate.mock.calls.map((c) =>
				JSON.stringify(c[0]?.queryKey),
			);
			expect(keys).toContain(JSON.stringify(query.summary.key));
			expect(keys).toContain(JSON.stringify(query.all_vacancies.key));
		});
	});
});
