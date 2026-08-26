export type ResizeDirection =
	| "North"
	| "South"
	| "East"
	| "West"
	| "NorthEast"
	| "NorthWest"
	| "SouthEast"
	| "SouthWest";

export interface WindowBridge {
	minimize(): void;
	toggleMaximize(): void;
	close(): void;
	isMaximized(): Promise<boolean>;
	onMaximizeChange(handler: (maximized: boolean) => void): () => void;
	startResize(direction: ResizeDirection): void;
}

export interface ConsentBridge {
	load(): Promise<string | null>;
	save(text: string): Promise<void>;
}

export type LogLevel = "debug" | "info" | "warn" | "error";

export interface UpdateInfo {
	version: string;
	body?: string;
}

export interface UpdaterBridge {
	check(): Promise<UpdateInfo | null>;
	install(): Promise<void>;
}

export interface OtklikBridge {
	getBackendPort(): Promise<number>;
	platform: string;
	window: WindowBridge;
	consent: ConsentBridge;
	openExternal(url: string): Promise<void>;
	appVersion(): Promise<string>;
	log(level: LogLevel, message: string): void;
	onBackendExit(handler: (detail?: string) => void): () => void;
	updater: UpdaterBridge;
}
