import { debug, error, info, warn } from "@tauri-apps/plugin-log";

export function getLogger(name: string) {
	const prefix = `[${name}]`;
	return {
		debug: (msg: string, ...args: unknown[]) =>
			debug(`${prefix} ${msg} ${args.length ? JSON.stringify(args) : ""}`),
		info: (msg: string, ...args: unknown[]) =>
			info(`${prefix} ${msg} ${args.length ? JSON.stringify(args) : ""}`),
		warn: (msg: string, ...args: unknown[]) =>
			warn(`${prefix} ${msg} ${args.length ? JSON.stringify(args) : ""}`),
		error: (msg: string, ...args: unknown[]) =>
			error(`${prefix} ${msg} ${args.length ? JSON.stringify(args) : ""}`),
	};
}
