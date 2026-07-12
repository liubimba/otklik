import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// $lib/log pulls in @tauri-apps/plugin-log, which calls window.__TAURI_INTERNALS__
// on every log line. In Node/jsdom that throws unhandled rejections and pollutes
// the report. Stub the module before importing the client so its top-level
// getLogger() gets the noop version.
vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

const { API } = await import("./client");
const { APIError } = await import("./error");

interface RecordedCall {
	url: string;
	init: RequestInit | undefined;
}

let calls: RecordedCall[] = [];
let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown, status = 200): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { "Content-Type": "application/json" },
	});
}

function textResponse(body: string, status = 200): Response {
	return new Response(body, {
		status,
		headers: { "Content-Type": "text/plain" },
	});
}

function noContent(): Response {
	return new Response(null, { status: 204 });
}

beforeEach(() => {
	calls = [];
	// Stub only fetch — the client reads VITE_BACKEND_IP/PORT from
	// import.meta.env, which vitest resolves at import time. The URLs asserted
	// below use `/api/v1/…` — the host prefix is irrelevant to the test.
	fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
		calls.push({ url, init });
		return jsonResponse({});
	});
	vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
	vi.unstubAllGlobals();
});

function respondWith(response: Response): void {
	fetchMock.mockImplementationOnce(async (url: string, init?: RequestInit) => {
		calls.push({ url, init });
		return response;
	});
}

function respondWithSequence(...responses: Response[]): void {
	for (const response of responses) {
		respondWith(response);
	}
}

/**
 * Split a recorded request URL into its path and parsed query string.
 *
 * Not `new URL(...)`: the client interpolates VITE_BACKEND_IP/PORT, which come
 * from a gitignored .env. Without it the host reads `undefined:undefined`, and
 * a non-numeric port makes the URL parser throw — green locally, red on CI.
 * The host is irrelevant to these assertions anyway.
 */
function splitUrl(url: string): [string, URLSearchParams] {
	const [path, query = ""] = url.split("?");
	return [path, new URLSearchParams(query)];
}

function bodyOf(call: RecordedCall): unknown {
	const raw = call.init?.body;
	if (raw == null) return undefined;
	if (typeof raw !== "string") throw new Error("Non-string body in test");
	return JSON.parse(raw);
}

describe("API URL construction", () => {
	it("auth endpoints hit /api/v1/auth/*", async () => {
		respondWithSequence(
			jsonResponse({ status: "authorized" }),
			jsonResponse({ status: "authorizing" }),
			jsonResponse({ status: "unauthorized" }),
			jsonResponse({ status: "unauthorized" }),
		);
		await API.auth.status();
		await API.auth.signIn();
		await API.auth.signOut();
		await API.auth.signInCancel();

		expect(calls.map((c) => `${c.init?.method ?? "GET"} ${c.url}`)).toEqual([
			expect.stringMatching(/GET .*\/api\/v1\/auth\/status$/),
			expect.stringMatching(/POST .*\/api\/v1\/auth\/sign-in$/),
			expect.stringMatching(/POST .*\/api\/v1\/auth\/sign-out$/),
			expect.stringMatching(/POST .*\/api\/v1\/auth\/sign-in\/cancel$/),
		]);
	});

	it("search parse endpoints use /search/parse (not /search/vacancies)", async () => {
		respondWithSequence(
			jsonResponse({ search_id: "sid" }),
			jsonResponse({ search_id: "sid" }),
			jsonResponse({}),
		);
		await API.search.parse.start("https://hh.ru/x", 5, 25);
		await API.search.parse.current();
		await API.search.parse.cancel("sid");

		expect(calls[0].url).toMatch(/\/api\/v1\/search\/parse\/start$/);
		expect(bodyOf(calls[0])).toEqual({
			url: "https://hh.ru/x",
			max_pages: 5,
			max_vacancies: 25,
		});
		expect(calls[1].url).toMatch(/\/api\/v1\/search\/parse\/current$/);
		expect(calls[2].url).toMatch(/\/api\/v1\/search\/parse\/sid$/);
		expect(calls[2].init?.method).toBe("DELETE");
	});

	it("search history list hits GET /search/history", async () => {
		respondWith(jsonResponse([]));
		await API.search.history.list();

		expect(calls[0].url).toMatch(/\/api\/v1\/search\/history$/);
		expect(calls[0].init?.method ?? "GET").toBe("GET");
	});

	it("application endpoints route through /vacancies/{id}/application/*", async () => {
		respondWithSequence(
			jsonResponse({}), // get
			jsonResponse([]), // letters
			jsonResponse({}), // generate
			jsonResponse({}), // save
			jsonResponse({}), // skip
			jsonResponse({}), // retry
		);
		await API.application.get(42);
		await API.application.letters(42);
		await API.application.generate(42);
		await API.application.save(42, "hi");
		await API.application.skip(42);
		await API.application.retry(42);

		expect(calls.map((c) => c.url)).toEqual([
			expect.stringMatching(/\/api\/v1\/vacancies\/42\/application$/),
			expect.stringMatching(/\/api\/v1\/vacancies\/42\/application\/letters$/),
			expect.stringMatching(/\/api\/v1\/vacancies\/42\/application\/generate$/),
			expect.stringMatching(/\/api\/v1\/vacancies\/42\/application\/save$/),
			expect.stringMatching(/\/api\/v1\/vacancies\/42\/application\/skip$/),
			expect.stringMatching(/\/api\/v1\/vacancies\/42\/application\/retry$/),
		]);
		// save sends the letter in the body
		expect(bodyOf(calls[3])).toEqual({ text: "hi" });
	});

	it("system endpoints hit /api/v1/system/*", async () => {
		respondWithSequence(
			jsonResponse({}),
			jsonResponse({ status: "healthy" }),
			jsonResponse({}),
			jsonResponse({}),
		);
		await API.system.rateLimits();
		await API.system.aiHealth();
		await API.system.orchestrator.status();
		await API.system.orchestrator.resume();

		expect(calls[0].url).toMatch(/\/api\/v1\/system\/rate-limits$/);
		expect(calls[1].url).toMatch(/\/api\/v1\/system\/ai\/health$/);
		expect(calls[2].url).toMatch(/\/api\/v1\/system\/orchestrator\/status$/);
		expect(calls[3].url).toMatch(/\/api\/v1\/system\/orchestrator\/resume$/);
		expect(calls[3].init?.method).toBe("POST");
	});

	// The sidebar counter is driven entirely by this path. A typo here would not
	// throw — it would 404 quietly and the badge would simply never appear.
	// Note the collection is /applications (global summary), NOT the per-vacancy
	// /vacancies/{id}/application route.
	it("applications summary hits GET /api/v1/applications/summary", async () => {
		respondWith(jsonResponse({ needs_attention: 3 }));

		await expect(API.applications.summary()).resolves.toEqual({
			needs_attention: 3,
		});

		expect(calls[0].url).toMatch(/\/api\/v1\/applications\/summary$/);
		expect(calls[0].init?.method ?? "GET").toBe("GET");
	});
});

describe("API.application.submit — dirty-submit body semantics", () => {
	it("sends { text } when text is provided (atomic dirty-submit)", async () => {
		respondWith(jsonResponse({}));
		await API.application.submit(7, "final draft");

		expect(calls[0].url).toMatch(
			/\/api\/v1\/vacancies\/7\/application\/submit$/,
		);
		expect(bodyOf(calls[0])).toEqual({ text: "final draft" });
	});

	it("sends {} when text is omitted (submit existing letter)", async () => {
		respondWith(jsonResponse({}));
		await API.application.submit(7);

		expect(bodyOf(calls[0])).toEqual({});
	});
});

describe("Response handling", () => {
	it("throws APIError with detail from the JSON body on 4xx/5xx", async () => {
		respondWith(jsonResponse({ detail: "Vacancy not found" }, 404));
		await expect(API.vacancies.get(999)).rejects.toMatchObject({
			status: 404,
			detail: "Vacancy not found",
		});
	});

	it("flattens FastAPI-style validation errors from `detail`", async () => {
		respondWith(
			jsonResponse(
				{
					detail: [
						{ loc: ["body", "text"], msg: "String too short", type: "err" },
					],
				},
				422,
			),
		);
		try {
			await API.application.save(1, "");
			expect.unreachable();
		} catch (error) {
			expect(error).toBeInstanceOf(APIError);
			expect((error as InstanceType<typeof APIError>).status).toBe(422);
			expect((error as InstanceType<typeof APIError>).detail).toContain(
				"body.text: String too short",
			);
		}
	});

	it("tolerates a non-JSON error body", async () => {
		respondWith(textResponse("Internal Server Error", 500));
		await expect(API.vacancies.list()).rejects.toMatchObject({
			status: 500,
			detail: "unknown error",
		});
	});

	it("API.application.get returns null on 404 (api404Null path)", async () => {
		respondWith(jsonResponse({ detail: "not found" }, 404));
		const result = await API.application.get(1);
		expect(result).toBeNull();
	});

	it("API.application.get rethrows non-404 errors", async () => {
		respondWith(jsonResponse({ detail: "boom" }, 500));
		await expect(API.application.get(1)).rejects.toBeInstanceOf(APIError);
	});

	it("API.search.parse.current returns null on 204 (no active parse)", async () => {
		respondWith(noContent());
		const result = await API.search.parse.current();
		expect(result).toBeNull();
	});
});

describe("Vacancies + settings + filter endpoints", () => {
	it("GET /vacancies/ and GET /vacancies/{id}", async () => {
		respondWithSequence(jsonResponse([]), jsonResponse({ id: 7 }));
		await API.vacancies.list();
		await API.vacancies.get(7);

		expect(calls[0].url).toMatch(/\/api\/v1\/vacancies\/$/);
		expect(calls[0].init?.method ?? "GET").toBe("GET");
		expect(calls[1].url).toMatch(/\/api\/v1\/vacancies\/7$/);
	});

	it("listAll with no options hits /vacancies/all with no query string", async () => {
		respondWith(jsonResponse({ items: [], total: 0 }));
		await API.vacancies.listAll();

		expect(calls[0].url).toMatch(/\/api\/v1\/vacancies\/all$/);
		expect(calls[0].init?.method ?? "GET").toBe("GET");
	});

	it("listAll serialises limit and offset", async () => {
		respondWith(jsonResponse({ items: [], total: 0 }));
		await API.vacancies.listAll({ limit: 50, offset: 100 });

		expect(calls[0].url).toMatch(/\/vacancies\/all\?limit=50&offset=100$/);
	});

	it("listAll repeats the status key once per filter", async () => {
		respondWith(jsonResponse({ items: [], total: 0 }));
		await API.vacancies.listAll({ statuses: ["none", "error"], limit: 10 });

		const [path, query] = splitUrl(calls[0].url);
		expect(path).toMatch(/\/vacancies\/all$/);
		expect(query.getAll("status")).toEqual(["none", "error"]);
		expect(query.get("limit")).toBe("10");
	});

	it("listAll omits undefined params entirely", async () => {
		respondWith(jsonResponse({ items: [], total: 0 }));
		await API.vacancies.listAll({ statuses: undefined, limit: 25 });

		const [, query] = splitUrl(calls[0].url);
		expect(query.has("status")).toBe(false);
		expect(query.has("offset")).toBe(false);
		expect(query.has("q")).toBe(false);
		expect(query.get("limit")).toBe("25");
	});

	it("listAll sends the search text as `q`, encoded", async () => {
		respondWith(jsonResponse({ items: [], total: 0 }));
		await API.vacancies.listAll({ search: "python разработчик" });

		const [, query] = splitUrl(calls[0].url);
		expect(query.get("q")).toBe("python разработчик");
	});

	it("GET /settings and PUT /settings — body forwarded verbatim", async () => {
		respondWithSequence(jsonResponse({}), jsonResponse({}));
		await API.settings.get();
		const settingsPayload = {
			search: { max_pages: 5, max_vacancies: 50 },
			user: { auto_submit: false },
			rate_limits: {
				daily_limit: 30,
				hourly_limit: 5,
				min_delay_ms: 800,
				delay_jitter_ms: 400,
			},
			llm: {
				resume_text: "",
				letter_style: "",
				system_prompt: null,
				deployments: [],
			},
		};
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		await API.settings.update(settingsPayload as any);

		expect(calls[0].url).toMatch(/\/api\/v1\/settings$/);
		expect(calls[0].init?.method ?? "GET").toBe("GET");

		expect(calls[1].init?.method).toBe("PUT");
		expect(bodyOf(calls[1])).toEqual(settingsPayload);
	});

	it("search filter open/confirm/cancel URLs", async () => {
		respondWithSequence(
			jsonResponse({ session_id: "sid" }),
			jsonResponse({ url: "https://hh.ru/x" }),
			jsonResponse({}),
		);
		await API.search.filter.open();
		await API.search.filter.confirm("sid");
		await API.search.filter.cancel("sid");

		expect(calls[0].url).toMatch(/\/api\/v1\/search\/filter\/new$/);
		expect(calls[0].init?.method).toBe("POST");
		expect(calls[1].url).toMatch(/\/api\/v1\/search\/filter\/sid\/confirm$/);
		expect(calls[2].url).toMatch(/\/api\/v1\/search\/filter\/sid\/cancel$/);
	});

	it("Content-Type: application/json header is always set", async () => {
		respondWith(jsonResponse({}));
		await API.auth.status();

		const headers = new Headers(calls[0].init?.headers);
		expect(headers.get("Content-Type")).toBe("application/json");
	});

	it("start(url, undefined, undefined) sends nulls in the body", async () => {
		respondWith(jsonResponse({ search_id: "x" }));
		await API.search.parse.start("https://hh.ru/x");

		expect(bodyOf(calls[0])).toEqual({
			url: "https://hh.ru/x",
			max_pages: undefined,
			max_vacancies: undefined,
		});
	});
});
