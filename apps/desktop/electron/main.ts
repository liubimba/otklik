import { mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { BrowserWindow, app, ipcMain, session, shell } from "electron";
import log from "electron-log";
import { autoUpdater } from "electron-updater";
import { freePort } from "./free-port";
import { APP_URL, registerAppSchemePrivileged, serveApp } from "./protocol";
import { UPDATER_PROXY_BYPASS, resolveUpdaterProxy } from "./proxy";
import { Sidecar } from "./sidecar";

autoUpdater.autoDownload = false;
autoUpdater.logger = log;

const NO_FEED =
	/latest.*\.yml|404|cannot find|enotfound|net::|dev-app-update|no published/i;

function releaseBody(notes: unknown): string | undefined {
	if (typeof notes === "string") {
		return notes;
	}
	if (Array.isArray(notes)) {
		return notes
			.map((note) => (typeof note === "string" ? note : (note?.note ?? "")))
			.join("\n");
	}
	return undefined;
}

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
	const updaterProxy = resolveUpdaterProxy(process.env);
	if (updaterProxy) {
		log.info(`updater: routing downloads through proxy ${updaterProxy}`);
		await session.defaultSession.setProxy({
			proxyRules: updaterProxy,
			proxyBypassRules: UPDATER_PROXY_BYPASS,
		});
	}
	backendPort = await freePort();
	log.info(`backend spawning on port ${backendPort}`);
	sidecar.onExit((exit) => {
		log.error(`backend exited code=${exit.code}`);
		mainWindow?.webContents.send("backend-exited", exit);
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

ipcMain.handle("open-external", (_event, url: string) =>
	shell.openExternal(url),
);
ipcMain.handle("app-version", () => app.getVersion());
ipcMain.on("log", (_event, level: string, message: string) => {
	const levels: Record<string, (msg: string) => void> = {
		debug: log.debug,
		info: log.info,
		warn: log.warn,
		error: log.error,
	};
	(levels[level] ?? log.info)(message);
});

ipcMain.handle("updater:check", async () => {
	try {
		const result = await autoUpdater.checkForUpdates();
		if (result?.isUpdateAvailable && result.updateInfo) {
			return {
				version: result.updateInfo.version,
				body: releaseBody(result.updateInfo.releaseNotes),
			};
		}
		return null;
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		if (NO_FEED.test(message)) {
			log.info(`updater: no feed yet (${message})`);
			return null;
		}
		throw error;
	}
});
ipcMain.handle("updater:install", async () => {
	await autoUpdater.downloadUpdate();
	sidecar.kill();
	autoUpdater.quitAndInstall();
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
