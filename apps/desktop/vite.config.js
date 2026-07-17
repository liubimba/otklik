import { createRequire } from "node:module";
import path from "node:path";
import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { visualizer } from "rollup-plugin-visualizer";
import { defaultClientConditions, defineConfig } from "vite";

const host = process.env.TAURI_DEV_HOST;

const require = createRequire(import.meta.url);
/** @param {string} name */
const bitsUiSubmodule = (name) =>
	path.join(path.dirname(require.resolve("bits-ui")), `bits/${name}/index.js`);
const bitsUiDropdownMenuEntry = bitsUiSubmodule("dropdown-menu");
const bitsUiAccordionEntry = bitsUiSubmodule("accordion");
const bitsUiLabelEntry = bitsUiSubmodule("label");

const bitsUiTestShimId = "\0virtual:bits-ui-test-shim";

const svelteResolveConditions = [...defaultClientConditions, "svelte"];

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
				visualizer({
					filename: "build/stats.html",
					gzipSize: true,
					brotliSize: true,
					template: "treemap",
				}),
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
				sourcemap: "hidden",
			},

			clearScreen: false,
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
