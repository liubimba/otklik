import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

if (typeof window !== "undefined" && !window.matchMedia) {
	window.matchMedia = vi.fn().mockImplementation((query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: vi.fn(),
		removeListener: vi.fn(),
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
		dispatchEvent: vi.fn(),
	}));
}

if (typeof window !== "undefined" && !window.ResizeObserver) {
	window.ResizeObserver = class {
		#callback: ResizeObserverCallback;
		constructor(callback: ResizeObserverCallback) {
			this.#callback = callback;
		}
		observe(target: Element) {
			queueMicrotask(() => {
				this.#callback(
					[{ target } as ResizeObserverEntry],
					this as unknown as ResizeObserver,
				);
			});
		}
		unobserve() {}
		disconnect() {}
	} as unknown as typeof ResizeObserver;
}
if (
	typeof window !== "undefined" &&
	!("__stubbedGetBoundingClientRect" in Element.prototype)
) {
	const stubbedRect = () => ({
		x: 0,
		y: 0,
		top: 0,
		left: 0,
		bottom: 40,
		right: 200,
		width: 200,
		height: 40,
		toJSON() {
			return this;
		},
	});
	Element.prototype.getBoundingClientRect =
		stubbedRect as typeof Element.prototype.getBoundingClientRect;
	Element.prototype.getClientRects = () =>
		[stubbedRect()] as unknown as DOMRectList;
	Object.defineProperty(Element.prototype, "__stubbedGetBoundingClientRect", {
		value: true,
	});
	Object.defineProperty(document.documentElement, "clientWidth", {
		value: 1024,
	});
	Object.defineProperty(document.documentElement, "clientHeight", {
		value: 768,
	});
}

if (typeof window !== "undefined" && !window.IntersectionObserver) {
	window.IntersectionObserver = class {
		root = null;
		rootMargin = "";
		thresholds: ReadonlyArray<number> = [];
		observe() {}
		unobserve() {}
		disconnect() {}
		takeRecords() {
			return [];
		}
	} as unknown as typeof IntersectionObserver;
}
