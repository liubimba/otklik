import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

const { EventsWebSocket } = await import("./events");

/**
 * Fake WebSocket that captures constructor URL, and exposes triggers for
 * onopen/onclose/onmessage/onerror so tests can drive the state machine
 * synchronously.
 */
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

	// helpers to drive lifecycle
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

describe("EventsWebSocket — connection URL + lifecycle", () => {
	it("connects to /ws/events on the configured host", () => {
		const ws = new EventsWebSocket(() => {});
		ws.connect();
		expect(FakeWebSocket.last().url).toMatch(/\/ws\/events$/);
		expect(FakeWebSocket.last().url.startsWith("ws://")).toBe(true);
	});

	it("close() marks the socket closed and skips reconnect", () => {
		const ws = new EventsWebSocket(() => {});
		ws.connect();
		ws.close();
		FakeWebSocket.last().fireClose();
		vi.runAllTimers();
		// No second WebSocket should have been created after close.
		expect(FakeWebSocket.instances.length).toBe(1);
	});

	it("close() cancels a pending reconnect timer", () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 1_000,
		});
		ws.connect();
		FakeWebSocket.last().fireClose(); // schedules reconnect
		ws.close();
		vi.advanceTimersByTime(5_000);
		expect(FakeWebSocket.instances.length).toBe(1);
	});
});

describe("EventsWebSocket — message dispatch", () => {
	it("parses valid JSON and forwards it to onEvent", () => {
		const received: unknown[] = [];
		const ws = new EventsWebSocket((event) => received.push(event));
		ws.connect();
		FakeWebSocket.last().fireOpen();

		FakeWebSocket.last().fireMessage({
			type: "auth_changed",
			data: { status: "authorized" },
		});

		expect(received).toEqual([
			{ type: "auth_changed", data: { status: "authorized" } },
		]);
	});

	it("swallows malformed JSON without calling onEvent", () => {
		const received: unknown[] = [];
		const ws = new EventsWebSocket((event) => received.push(event));
		ws.connect();
		FakeWebSocket.last().fireOpen();

		FakeWebSocket.last().fireMessage("not-json");

		expect(received).toEqual([]);
	});
});

describe("EventsWebSocket — reconnect backoff", () => {
	it("reconnects after unclean close with the configured initial delay", () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 500,
			backoffFactor: 2,
			maxDelay: 10_000,
		});
		ws.connect();
		FakeWebSocket.last().fireClose(1006, false);

		expect(FakeWebSocket.instances.length).toBe(1);
		vi.advanceTimersByTime(499);
		expect(FakeWebSocket.instances.length).toBe(1);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances.length).toBe(2);
	});

	it("doubles delay after each failed attempt (exponential backoff)", () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 100,
			backoffFactor: 2,
			maxDelay: 10_000,
		});
		ws.connect();

		// First reconnect after 100 ms
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(100);
		expect(FakeWebSocket.instances.length).toBe(2);

		// Second reconnect after 200 ms (100 * 2)
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(199);
		expect(FakeWebSocket.instances.length).toBe(2);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances.length).toBe(3);

		// Third reconnect after 400 ms (200 * 2)
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(399);
		expect(FakeWebSocket.instances.length).toBe(3);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances.length).toBe(4);
	});

	it("caps the delay at maxDelay", () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 100,
			backoffFactor: 10,
			maxDelay: 500,
		});
		ws.connect();

		// 100 ms → 500 (capped, was going to be 1_000) → 500 (still capped)
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(100);
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(500);
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(500);
		expect(FakeWebSocket.instances.length).toBe(4);
	});

	it("resets backoff after a successful open", () => {
		const ws = new EventsWebSocket(() => {}, undefined, undefined, {
			initialDelay: 100,
			backoffFactor: 2,
		});
		ws.connect();
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(100); // reconnect #2
		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(200); // reconnect #3, delay doubled to 200
		FakeWebSocket.last().fireOpen(); // success — reset
		FakeWebSocket.last().fireClose();
		// After reset, next reconnect should fire at initialDelay again.
		vi.advanceTimersByTime(99);
		const before = FakeWebSocket.instances.length;
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances.length).toBe(before + 1);
	});

	it("stops reconnecting once maxAttempts is reached and fires onClose", () => {
		const onClose = vi.fn();
		const ws = new EventsWebSocket(() => {}, undefined, onClose, {
			initialDelay: 10,
			maxAttempts: 2,
		});
		ws.connect();

		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(10); // attempt #2 socket created

		FakeWebSocket.last().fireClose();
		vi.advanceTimersByTime(20); // attempt #3 would fire here

		FakeWebSocket.last().fireClose();
		vi.runAllTimers();

		expect(FakeWebSocket.instances.length).toBeLessThanOrEqual(3);
		expect(onClose).toHaveBeenCalled();
	});
});

describe("EventsWebSocket — open hook", () => {
	it("calls onOpen on the first successful connect", () => {
		const onOpen = vi.fn();
		const ws = new EventsWebSocket(
			() => {},
			undefined,
			undefined,
			undefined,
			onOpen,
		);
		ws.connect();
		expect(onOpen).not.toHaveBeenCalled();
		FakeWebSocket.last().fireOpen();
		expect(onOpen).toHaveBeenCalledTimes(1);
	});

	it("calls onOpen again on every reconnect, not just the first connect", () => {
		const onOpen = vi.fn();
		const ws = new EventsWebSocket(
			() => {},
			undefined,
			undefined,
			{ initialDelay: 100 },
			onOpen,
		);
		ws.connect();
		FakeWebSocket.last().fireOpen();
		expect(onOpen).toHaveBeenCalledTimes(1);

		// Socket drops and reconnects — this is the "may have missed events"
		// case the hook exists for (WS gap / boot race in the bug report).
		FakeWebSocket.last().fireClose(1006, false);
		vi.advanceTimersByTime(100);
		FakeWebSocket.last().fireOpen();
		expect(onOpen).toHaveBeenCalledTimes(2);
	});
});

describe("EventsWebSocket — error hook", () => {
	it("propagates onerror to the caller-supplied handler", () => {
		const onError = vi.fn();
		const ws = new EventsWebSocket(() => {}, onError);
		ws.connect();
		FakeWebSocket.last().fireError();
		expect(onError).toHaveBeenCalledTimes(1);
	});
});
