import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { BrowserWindow, app } from "electron";
import { APP_URL, registerAppSchemePrivileged, serveApp } from "./protocol";

const devUrl = process.env.ELECTRON_RENDERER_URL;
const shotPath = process.env.ELECTRON_SHOT;
const rendererRoot = join(__dirname, "..", "build");

registerAppSchemePrivileged();

function createWindow(): void {
	const win = new BrowserWindow({
		width: 1200,
		height: 800,
		frame: false,
		backgroundColor: "#0b0b0f",
		webPreferences: {
			preload: join(__dirname, "preload.cjs"),
			contextIsolation: true,
			nodeIntegration: false,
		},
	});
	if (devUrl) {
		void win.loadURL(devUrl);
	} else {
		void win.loadURL(APP_URL);
	}
	if (shotPath) {
		win.webContents.on("did-finish-load", () => {
			setTimeout(() => {
				void win.webContents.capturePage().then(async (img) => {
					await writeFile(shotPath, img.toPNG());
					app.quit();
				});
			}, 3000);
		});
	}
}

app.whenReady().then(() => {
	serveApp(rendererRoot);
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
