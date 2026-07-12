import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom does not implement matchMedia. `dotted-background.svelte` and any UI
// code that reads a media query breaks without this. Tests that need to
// simulate a matching query override this stub in-place.
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

// jsdom implements neither observer either. bits-ui's floating-layer (used
// by DropdownMenu/Popover/Select/Tooltip content positioning) constructs a
// real `ResizeObserver` unconditionally; without a stub the constructor
// throws mid-effect, which silently aborts mounting the portalled content
// (and is the source of Svelte's "derived_inert" warning in those tests).
//
// The callback must actually fire once after `observe()` (a real
// ResizeObserver always reports an initial entry, asynchronously) — Floating
// UI's `autoUpdate` waits on that first callback to run its position
// computation. A no-op stub never calls back, so the floating content stays
// permanently `visibility: hidden` and is invisible to accessibility
// queries.
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
// jsdom never runs layout, so every element's `getBoundingClientRect()` is a
// degenerate {0,0,0,0} and `documentElement.clientHeight` is 0. Floating UI
// (bits-ui's positioning engine) reads both to size the "available space"
// around an anchor; with zero space everywhere it concludes there's no room
// and keeps the floating content `visibility: hidden` forever — the
// standard, documented gap when testing Radix/Floating-UI-style popovers
// under jsdom. A fixed, plausible rect is enough for it to compute a real
// (if arbitrary) position instead.
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
	// Floating UI treats an anchor with zero `getClientRects()` as "hidden"
	// (`isReferenceHidden` in its position-update logic) and refuses to ever
	// mark the floating content positioned — jsdom's default `getClientRects`
	// is always empty, so without this the content stays permanently
	// `visibility: hidden`, invisible to every accessibility query, forever.
	Element.prototype.getClientRects = () =>
		[stubbedRect()] as unknown as DOMRectList;
	Object.defineProperty(Element.prototype, "__stubbedGetBoundingClientRect", {
		value: true,
	});
	// Floating UI's viewport boundary uses `clientWidth`/`clientHeight`
	// (always 0 in jsdom, no getBoundingClientRect involved) separately from
	// the rect above — stub those too or "available space" still computes as
	// negative regardless of the anchor's own rect.
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
