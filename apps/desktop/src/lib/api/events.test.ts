import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
	invoke: () => Promise.resolve(8001),
}));

vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

const { EventsWebSocket } = await import("./events");

class FakeWebSocket {
	static instances: FakeWebSocket[] = [];
	static reset(): void {
		FakeWebSocket.instances = [];
	}
	static last(): FakeWebSocket {
		const ws = FakeWebSocket.instances.at(-1);
		if (!ws) throw new Error("No WebSocket instance created yet");
		return ws;
	}

	url: string;
	onopen: ((ev: Event) => void) | null = null;
	onclose: ((ev: CloseEvent) => void) | null = null;
	onmessage: ((ev: MessageEvent) => void) | null = null;
	onerror: ((ev: Event) => void) | null = null;
	closed = false;

	constructor(url: string) {
		this.url = url;
		FakeWebSocket.instances.push(this);
	}

	close(): void {
		this.closed = true;
	}

	fireOpen(): void {
		this.onopen?.(new Event("open"));
	}
	fireClose(code = 1000, wasClean = true): void {
		this.onclose?.({ code, wasClean } as unknown as CloseEvent);
	}
	fireMessage(data: unknown): void {
		this.onmessage?.({
			data: typeof data === "string" ? data : JSON.stringify(data),
		} as MessageEvent);
	}
	fireError(): void {
		this.onerror?.(new Event("error"));
	}
}

beforeEach(() => {
	FakeWebSocket.reset();
	vi.stubGlobal("WebSocket", FakeWebSocket);
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

const flush = async (): Promise<void> => {
	await vi.advanceTimersByTimeAsync(0);
};

describe("EventsWebSocket — connection URL + lifecycle", () => {
	it("connects to /ws/events on the configured host", async () => {
		const ws = new EventsWebSocket(() => {});
		ws.connect();
		await flush();
		expect(FakeWebSocket.last().url).toMatch(/\/ws\/events$/);
		expect(FakeWebSocket.last().url.startsWith("ws://")).toBe(true);
	});

	it("close() marks the socket closed and skips reconnect", async () => {
		const ws = new EventsWebSocket(() => {});
		ws.connect();
		await flush();
		ws.close();
		FakeWebSocket.last().fireClose();
		vi.runAllTimers();
		expect(FakeWebSocket.instances.length).toBe(1);
	});

	it("close() cancels a pending reconnect timer", async () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 1_000,
		});
		ws.connect();
		await flush();
		FakeWebSocket.last().fireClose();
		ws.close();
		await vi.advanceTimersByTimeAsync(5_000);
		expect(FakeWebSocket.instances.length).toBe(1);
	});
});

describe("EventsWebSocket — message dispatch", () => {
	it("parses valid JSON and forwards it to onEvent", async () => {
		const received: unknown[] = [];
		const ws = new EventsWebSocket((event) => received.push(event));
		ws.connect();
		await flush();
		FakeWebSocket.last().fireOpen();

		FakeWebSocket.last().fireMessage({
			type: "auth_changed",
			data: { status: "authorized" },
		});

		expect(received).toEqual([
			{ type: "auth_changed", data: { status: "authorized" } },
		]);
	});

	it("swallows malformed JSON without calling onEvent", async () => {
		const received: unknown[] = [];
		const ws = new EventsWebSocket((event) => received.push(event));
		ws.connect();
		await flush();
		FakeWebSocket.last().fireOpen();

		FakeWebSocket.last().fireMessage("not-json");

		expect(received).toEqual([]);
	});
});

describe("EventsWebSocket — reconnect backoff", () => {
	it("reconnects after unclean close with the configured initial delay", async () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 500,
			backoffFactor: 2,
			maxDelay: 10_000,
		});
		ws.connect();
		await flush();
		FakeWebSocket.last().fireClose(1006, false);

		expect(FakeWebSocket.instances.length).toBe(1);
		await vi.advanceTimersByTimeAsync(499);
		expect(FakeWebSocket.instances.length).toBe(1);
		await vi.advanceTimersByTimeAsync(1);
		expect(FakeWebSocket.instances.length).toBe(2);
	});

	it("doubles delay after each failed attempt (exponential backoff)", async () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 100,
			backoffFactor: 2,
			maxDelay: 10_000,
		});
		ws.connect();
		await flush();

		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(100);
		expect(FakeWebSocket.instances.length).toBe(2);

		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(199);
		expect(FakeWebSocket.instances.length).toBe(2);
		await vi.advanceTimersByTimeAsync(1);
		expect(FakeWebSocket.instances.length).toBe(3);

		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(399);
		expect(FakeWebSocket.instances.length).toBe(3);
		await vi.advanceTimersByTimeAsync(1);
		expect(FakeWebSocket.instances.length).toBe(4);
	});

	it("caps the delay at maxDelay", async () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 100,
			backoffFactor: 10,
			maxDelay: 500,
		});
		ws.connect();
		await flush();

		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(100);
		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(500);
		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(500);
		expect(FakeWebSocket.instances.length).toBe(4);
	});

	it("resets backoff after a successful open", async () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 100,
			backoffFactor: 2,
		});
		ws.connect();
		await flush();
		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(100);
		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(200);
		FakeWebSocket.last().fireOpen();
		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(99);
		const before = FakeWebSocket.instances.length;
		await vi.advanceTimersByTimeAsync(1);
		expect(FakeWebSocket.instances.length).toBe(before + 1);
	});

	it("stops reconnecting once maxAttempts is reached and fires onClose", async () => {
		const onClose = vi.fn();
		const ws = new EventsWebSocket(() => {}, undefined, onClose, {
			initialDelay: 10,
			maxAttempts: 2,
		});
		ws.connect();
		await flush();

		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(10);

		FakeWebSocket.last().fireClose();
		await vi.advanceTimersByTimeAsync(20);

		FakeWebSocket.last().fireClose();
		vi.runAllTimers();

		expect(FakeWebSocket.instances.length).toBeLessThanOrEqual(3);
		expect(onClose).toHaveBeenCalled();
	});
});

describe("EventsWebSocket — open hook", () => {
	it("calls onOpen on the first successful connect", async () => {
		const onOpen = vi.fn();
		const ws = new EventsWebSocket(
			() => {},
			undefined,
			undefined,
			undefined,
			onOpen,
		);
		ws.connect();
		await flush();
		expect(onOpen).not.toHaveBeenCalled();
		FakeWebSocket.last().fireOpen();
		expect(onOpen).toHaveBeenCalledTimes(1);
	});

	it("calls onOpen again on every reconnect, not just the first connect", async () => {
		const onOpen = vi.fn();
		const ws = new EventsWebSocket(
			() => {},
			undefined,
			undefined,
			{ initialDelay: 100 },
			onOpen,
		);
		ws.connect();
		await flush();
		FakeWebSocket.last().fireOpen();
		expect(onOpen).toHaveBeenCalledTimes(1);

		FakeWebSocket.last().fireClose(1006, false);
		await vi.advanceTimersByTimeAsync(100);
		FakeWebSocket.last().fireOpen();
		expect(onOpen).toHaveBeenCalledTimes(2);
	});
});

describe("EventsWebSocket — disconnect hook", () => {
	function withDisconnect(onDisconnect: () => void, options = {}) {
		return new EventsWebSocket(
			() => {},
			undefined,
			undefined,
			options,
			undefined,
			onDisconnect,
		);
	}

	it("fires onDisconnect when an established socket drops unexpectedly", async () => {
		const onDisconnect = vi.fn();
		const ws = withDisconnect(onDisconnect, { initialDelay: 100 });
		ws.connect();
		await flush();
		FakeWebSocket.last().fireOpen();
		FakeWebSocket.last().fireClose(1006, false);
		expect(onDisconnect).toHaveBeenCalledTimes(1);
	});

	it("does NOT fire onDisconnect on an intentional close() — that's onClose's job", async () => {
		const onDisconnect = vi.fn();
		const ws = withDisconnect(onDisconnect);
		ws.connect();
		await flush();
		FakeWebSocket.last().fireOpen();
		ws.close();
		FakeWebSocket.last().fireClose();
		expect(onDisconnect).not.toHaveBeenCalled();
	});

	it("fires onDisconnect when the socket cannot even be opened", async () => {
		vi.stubGlobal(
			"WebSocket",
			class {
				constructor() {
					throw new SyntaxError("bad url");
				}
			},
		);
		const onDisconnect = vi.fn();
		const ws = withDisconnect(onDisconnect);
		ws.connect();
		await flush();
		expect(onDisconnect).toHaveBeenCalledTimes(1);
		ws.close();
	});
});

describe("EventsWebSocket — error hook", () => {
	it("propagates onerror to the caller-supplied handler", async () => {
		const onError = vi.fn();
		const ws = new EventsWebSocket(() => {}, onError);
		ws.connect();
		await flush();
		FakeWebSocket.last().fireError();
		expect(onError).toHaveBeenCalledTimes(1);
	});
});

describe("EventsWebSocket — a bad URL must not take the app down", () => {
	it("does not throw when the WebSocket constructor rejects the url", async () => {
		vi.stubGlobal(
			"WebSocket",
			class {
				constructor() {
					throw new SyntaxError(
						"The string did not match the expected pattern.",
					);
				}
			},
		);

		const ws = new EventsWebSocket(() => {});

		expect(() => ws.connect()).not.toThrow();

		ws.close();
	});

	it("reports the failure through onError instead of throwing", async () => {
		vi.stubGlobal(
			"WebSocket",
			class {
				constructor() {
					throw new SyntaxError(
						"The string did not match the expected pattern.",
					);
				}
			},
		);
		const onError = vi.fn();

		const ws = new EventsWebSocket(() => {}, onError);
		ws.connect();
		await flush();

		expect(onError).toHaveBeenCalledTimes(1);

		ws.close();
	});
});
