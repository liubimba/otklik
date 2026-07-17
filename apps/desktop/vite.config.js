import { createRequire } from "node:module";
import path from "node:path";
import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { visualizer } from "rollup-plugin-visualizer";
import { defaultClientConditions, defineConfig } from "vite";

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
// A single aliased submodule only covers one primitive, but different
// tests need different primitives from the same "bits-ui" specifier (e.g.
// account-cell.test.ts needs DropdownMenu, settings-ai-tab.test.ts needs
// Accordion and Label — formsnap's Form.Label renders `$lib/components/ui/
// label`, which is a thin wrapper over bits-ui's Label). So instead of
// aliasing to one submodule's file, alias to a tiny virtual module (below)
// that re-exports each needed primitive from its own style-tag-free
// submodule. Add a submodule entry here — and a matching
// `export { X } from ...` line in the virtual module — the next time a test
// needs another bits-ui primitive (Sheet, Tooltip, ...).
const require = createRequire(import.meta.url);
/** @param {string} name */
const bitsUiSubmodule = (name) =>
	path.join(path.dirname(require.resolve("bits-ui")), `bits/${name}/index.js`);
const bitsUiDropdownMenuEntry = bitsUiSubmodule("dropdown-menu");
const bitsUiAccordionEntry = bitsUiSubmodule("accordion");
const bitsUiLabelEntry = bitsUiSubmodule("label");

const bitsUiTestShimId = "\0virtual:bits-ui-test-shim";

// Second, distinct symptom of the same private-old-vite-copy issue: several
// svelte-ecosystem packages (`formsnap`, its dependency `svelte-toolbelt`)
// declare an exports map with ONLY a "svelte" condition and no
// "default"/"import" fallback, e.g.:
//   "exports": { ".": { "types": "...", "svelte": "./dist/index.js" } }
// The main sveltekit()-managed vite instance gets that "svelte" resolve
// condition pushed onto it at runtime by vite-plugin-svelte's `config()`
// hook, so this resolves fine in dev/build. @vitest/mocker's private vite
// copy never runs that plugin hook, so it never gets the condition, and
// resolving e.g. "formsnap" through it throws `ERR_PACKAGE_PATH_NOT_EXPORTED`
// outright the moment any test renders a component that touches
// `$lib/components/ui/form`.
//
// Declaring the condition statically here (rather than relying on the
// plugin to inject it at runtime) reaches both vite instances, since it's
// plain config data both read — no per-package alias needed.
//
// ОБЯЗАТЕЛЬНО со спредом defaultClientConditions: resolve.conditions
// ЗАМЕЩАЕТ дефолты вайта, а не дополняет их. Голый ["svelte"] выкидывает
// "browser", и клиентский бандл начинает резолвить svelte по ветке
// "default" её exports-мапы — то есть на СЕРВЕРНУЮ сборку: onDestroy падает
// на любой странице с superForm (Настройки), onMount становится no-op'ом,
// svelte/reactivity подменяется нереактивными заглушками внутри
// bits-ui/runed, а untrack вырождается в (fn) => fn(). Ни один гейт этого
// не увидит: svelteTesting() возвращает "browser" обратно, но только когда
// выставлен process.env.VITEST — то есть тесты, pnpm check и pnpm build
// остаются зелёными на сломанном dev/prod.
const svelteResolveConditions = [...defaultClientConditions, "svelte"];

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
				// Backs the `bits-ui` test alias below: resolves the virtual id to
				// a module re-exporting each style-tag-free submodule under its
				// real "bits-ui" export name. See the comment above
				// `bitsUiSubmodule` for why this exists instead of aliasing
				// straight to the package.
				{
					name: "bits-ui-test-shim",
					resolveId(id) {
						if (id === bitsUiTestShimId) return bitsUiTestShimId;
					},
					load(id) {
						if (id !== bitsUiTestShimId) return;
						return [
							`export { DropdownMenu } from ${JSON.stringify(bitsUiDropdownMenuEntry)};`,
							`export { Accordion } from ${JSON.stringify(bitsUiAccordionEntry)};`,
							`export { Label } from ${JSON.stringify(bitsUiLabelEntry)};`,
						].join("\n");
					},
				},
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

			resolve: {
				conditions: svelteResolveConditions,
			},

			test: {
				include: ["src/**/*.{test,spec}.{js,ts}"],
				exclude: ["src-tauri/**", "node_modules/**"],
				environment: "jsdom",
				setupFiles: ["./src/lib/test-setup.ts"],
				alias: [{ find: /^bits-ui$/, replacement: bitsUiTestShimId }],
			},
		}),
);
