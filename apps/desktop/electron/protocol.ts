import { readFile } from "node:fs/promises";
import { join, normalize } from "node:path";
import { protocol } from "electron";

export const APP_SCHEME = "app";
export const APP_URL = "app://bundle/";

const MIME: Record<string, string> = {
	".html": "text/html",
	".js": "text/javascript",
	".mjs": "text/javascript",
	".css": "text/css",
	".json": "application/json",
	".svg": "image/svg+xml",
	".png": "image/png",
	".jpg": "image/jpeg",
	".webp": "image/webp",
	".ico": "image/x-icon",
	".woff": "font/woff",
	".woff2": "font/woff2",
	".ttf": "font/ttf",
	".wasm": "application/wasm",
	".map": "application/json",
};

function contentType(path: string): string {
	const dot = path.lastIndexOf(".");
	const ext = dot === -1 ? "" : path.slice(dot).toLowerCase();
	return MIME[ext] ?? "application/octet-stream";
}

export function registerAppSchemePrivileged(): void {
	protocol.registerSchemesAsPrivileged([
		{
			scheme: APP_SCHEME,
			privileges: {
				standard: true,
				secure: true,
				supportFetchAPI: true,
				corsEnabled: true,
			},
		},
	]);
}

export function serveApp(root: string): void {
	const base = normalize(root);
	protocol.handle(APP_SCHEME, async (request) => {
		const { pathname } = new URL(request.url);
		const decoded = decodeURIComponent(pathname);
		const rel = decoded === "/" ? "/index.html" : decoded;
		const target = normalize(join(base, rel));
		const filePath = target.startsWith(base)
			? target
			: join(base, "index.html");
		try {
			const data = await readFile(filePath);
			return new Response(data, {
				headers: { "content-type": contentType(filePath) },
			});
		} catch {
			const fallback = await readFile(join(base, "index.html"));
			return new Response(fallback, {
				headers: { "content-type": "text/html" },
			});
		}
	});
}
