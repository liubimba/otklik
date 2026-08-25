import { mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { BrowserWindow, app, ipcMain } from "electron";
import { freePort } from "./free-port";
import { APP_URL, registerAppSchemePrivileged, serveApp } from "./protocol";
import { Sidecar } from "./sidecar";

const devUrl = process.env.ELECTRON_RENDERER_URL;
const shotPath = process.env.ELECTRON_SHOT;
const rendererRoot = join(__dirname, "..", "build");

const sidecar = new Sidecar();
let backendPort = 0;
let mainWindow: BrowserWindow | null = null;

registerAppSchemePrivileged();

function backendBinPath(): string {
	const name =
		process.platform === "win32" ? "otklik-backend.exe" : "otklik-backend";
	if (app.isPackaged) {
		return join(process.resourcesPath, "backend", name);
	}
	return join(
		__dirname,
		"..",
		"..",
		"..",
		"services",
		"backend",
		".venv",
		"bin",
		name,
	);
}

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
	mainWindow = win;
	win.on("closed", () => {
		mainWindow = null;
	});
	win.on("maximize", () => {
		win.webContents.send("window:maximize-change", true);
	});
	win.on("unmaximize", () => {
		win.webContents.send("window:maximize-change", false);
	});
	if (!app.isPackaged) {
		win.webContents.on("console-message", (_e, _lvl, message) => {
			console.log("[renderer]", message);
		});
		win.webContents.on("did-fail-load", (_e, code, desc, url) => {
			console.log("[did-fail-load]", code, desc, url);
		});
	}
	if (devUrl) {
		void win.loadURL(devUrl);
	} else {
		void win.loadURL(APP_URL);
	}
	if (shotPath) {
		const delay = Number(process.env.ELECTRON_SHOT_DELAY ?? "3000");
		win.webContents.on("did-finish-load", () => {
			setTimeout(() => {
				void win.webContents.capturePage().then(async (img) => {
					await writeFile(shotPath, img.toPNG());
					app.quit();
				});
			}, delay);
		});
	}
}

app.whenReady().then(async () => {
	serveApp(rendererRoot);
	backendPort = await freePort();
	console.log("[main] backend port", backendPort, "bin", backendBinPath());
	sidecar.onExit((exit) => {
		console.log("[main] backend exited", exit.code, exit.stderr.slice(-800));
	});
	sidecar.start(backendBinPath(), backendPort);
	createWindow();
	app.on("activate", () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			createWindow();
		}
	});
});

ipcMain.handle("get-backend-port", () => backendPort);

ipcMain.on("window:minimize", () => mainWindow?.minimize());
ipcMain.on("window:toggle-maximize", () => {
	if (!mainWindow) return;
	if (mainWindow.isMaximized()) {
		mainWindow.unmaximize();
	} else {
		mainWindow.maximize();
	}
});
ipcMain.on("window:close", () => mainWindow?.close());
ipcMain.handle("window:is-maximized", () => mainWindow?.isMaximized() ?? false);
ipcMain.on("window:start-resize", () => {});

const consentPath = join(homedir(), ".otklik", "consent.json");
const legacyConsentPath = join(homedir(), ".headhunter_ai", "consent.json");

ipcMain.handle("consent:load", async () => {
	for (const path of [consentPath, legacyConsentPath]) {
		const text = await readFile(path, "utf-8").catch(() => null);
		if (text !== null) {
			return text;
		}
	}
	return null;
});
ipcMain.handle("consent:save", async (_event, text: string) => {
	await mkdir(join(homedir(), ".otklik"), { recursive: true });
	await writeFile(consentPath, text, "utf-8");
});

app.on("before-quit", () => {
	sidecar.kill();
});

app.on("window-all-closed", () => {
	sidecar.kill();
	if (process.platform !== "darwin") {
		app.quit();
	}
});
