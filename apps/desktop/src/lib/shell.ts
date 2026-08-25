import type { OtklikBridge } from "./shell-types";

export function shell(): OtklikBridge {
	const bridge = (globalThis as { otklik?: OtklikBridge }).otklik;
	if (!bridge) {
		throw new Error("otklik shell bridge unavailable");
	}
	return bridge;
}
