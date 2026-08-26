import type { LogLevel, OtklikBridge } from "$lib/shell-types";

function emit(level: LogLevel, line: string): void {
	const bridge = (globalThis as { otklik?: OtklikBridge }).otklik;
	if (bridge) {
		bridge.log(level, line);
	} else {
		console[level](line);
	}
}

export function getLogger(name: string) {
	const prefix = `[${name}]`;
	const format = (msg: string, args: unknown[]): string =>
		`${prefix} ${msg} ${args.length ? JSON.stringify(args) : ""}`;
	return {
		debug: (msg: string, ...args: unknown[]) =>
			emit("debug", format(msg, args)),
		info: (msg: string, ...args: unknown[]) => emit("info", format(msg, args)),
		warn: (msg: string, ...args: unknown[]) => emit("warn", format(msg, args)),
		error: (msg: string, ...args: unknown[]) =>
			emit("error", format(msg, args)),
	};
}
