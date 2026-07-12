import { createRequire } from "node:module";
import path from "node:path";
import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { visualizer } from "rollup-plugin-visualizer";
import { defineConfig } from "vite";

const host = process.env.TAURI_DEV_HOST;

// Test-only workaround for a real vitest/vite-plugin-svelte incompatibility
// (vitest 2's bundled @vitest/mocker drags in a private, older `vite` copy;
// vite-plugin-svelte's CSS preprocessor then crashes — "Cannot create proxy
// with a non-object as target or handler" — while compiling ANY `<style>`
// tag reached through the module graph. See
// https://github.com/sveltejs/vite-plugin-svelte/issues/1043; upstream fix
// is "upgrade to vitest 3", out of scope here).
//
// `bits-ui`'s package.json only exposes a single "." entry point, and that
// entry eagerly re-exports every primitive it ships — including Select,
// whose `select-viewport.svelte` has a literal `<style>` block. So merely
// importing `DropdownMenu` from "bits-ui" pulls Select's style tag into the
// graph and trips the crash, even though we never use Select.
//
// `bits-ui/dist/bits/dropdown-menu/index.js` has no such style tag anywhere
// in its own subtree, so aliasing straight to it — bypassing the barrel —
// sidesteps the bug without touching dependencies or lockfiles. Resolved
// via `require.resolve("bits-ui")` (the one path Node's `exports` field
// actually allows) rather than a deep bare import, which the `exports`
// field would reject.
//
// NOTE: this only covers DropdownMenu. A future test that renders a
// different bits-ui primitive (Sheet, Accordion, Tooltip, ...) will hit the
// same crash and need the same treatment — widen this alias, don't remove
// it.
const require = createRequire(import.meta.url);
const bitsUiDropdownMenuEntry = path.join(
	path.dirname(require.resolve("bits-ui")),
	"bits/dropdown-menu/index.js",
);

// https://vite.dev/config/
export default defineConfig(
	() =>
		/** @type {import("vite").UserConfig} */ ({
			plugins: [
				paraglideVitePlugin({
					project: "./project.inlang",
					outdir: "./src/lib/paraglide",
				}),
				sveltekit(),
				tailwindcss(),
				svelteTesting(),
				// Bundle treemap for perf audits. Emitted to `build/stats.html`
				// after `pnpm build`. Not enabled in dev — the plugin runs during
				// the rollup build phase only.
				visualizer({
					filename: "build/stats.html",
					gzipSize: true,
					brotliSize: true,
					template: "treemap",
				}),
			],

			build: {
				// Hidden source maps: keep the .map files next to the chunks so
				// DevTools can symbolicate stack traces and rollup-plugin-visualizer
				// can name treemap boxes, but do NOT append the sourceMappingURL
				// comment so the shipped bundle stays clean.
				sourcemap: "hidden",
			},

			// Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
			//
			// 1. prevent Vite from obscuring rust errors
			clearScreen: false,
			// 2. tauri expects a fixed port, fail if that port is not available
			server: {
				port: 1420,
				strictPort: true,
				host: host || false,
				hmr: host
					? {
							protocol: "ws",
							host,
							port: 1421,
						}
					: undefined,
				watch: {
					// 3. tell Vite to ignore watching `src-tauri`
					ignored: ["**/src-tauri/**"],
				},
			},

			test: {
				include: ["src/**/*.{test,spec}.{js,ts}"],
				exclude: ["src-tauri/**", "node_modules/**"],
				environment: "jsdom",
				setupFiles: ["./src/lib/test-setup.ts"],
				alias: [{ find: /^bits-ui$/, replacement: bitsUiDropdownMenuEntry }],
			},
		}),
);
