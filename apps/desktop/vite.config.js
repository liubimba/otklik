import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { visualizer } from "rollup-plugin-visualizer";
import { defineConfig } from "vite";

const host = process.env.TAURI_DEV_HOST;

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
			},
		}),
);
