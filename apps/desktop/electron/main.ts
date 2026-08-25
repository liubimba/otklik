import { BrowserWindow, app } from "electron";

function createWindow(): void {
	const win = new BrowserWindow({ width: 1200, height: 800 });
	void win.loadURL("about:blank");
}

app.whenReady().then(() => {
	createWindow();
	app.on("activate", () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			createWindow();
		}
	});
});

app.on("window-all-closed", () => {
	if (process.platform !== "darwin") {
		app.quit();
	}
});
