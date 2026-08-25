import { type IpcRendererEvent, contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("otklik", {
	getBackendPort: (): Promise<number> => ipcRenderer.invoke("get-backend-port"),
	platform: process.platform,
	window: {
		minimize: () => ipcRenderer.send("window:minimize"),
		toggleMaximize: () => ipcRenderer.send("window:toggle-maximize"),
		close: () => ipcRenderer.send("window:close"),
		isMaximized: (): Promise<boolean> =>
			ipcRenderer.invoke("window:is-maximized"),
		onMaximizeChange: (handler: (maximized: boolean) => void): (() => void) => {
			const listener = (_event: IpcRendererEvent, maximized: boolean): void =>
				handler(maximized);
			ipcRenderer.on("window:maximize-change", listener);
			return () => {
				ipcRenderer.removeListener("window:maximize-change", listener);
			};
		},
		startResize: (direction: string) =>
			ipcRenderer.send("window:start-resize", direction),
	},
	consent: {
		load: (): Promise<string | null> => ipcRenderer.invoke("consent:load"),
		save: (text: string): Promise<void> =>
			ipcRenderer.invoke("consent:save", text),
	},
});
