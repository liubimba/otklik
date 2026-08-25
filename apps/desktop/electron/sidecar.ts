import { type ChildProcess, spawn } from "node:child_process";

const STDERR_CAP = 4000;

export interface BackendExit {
	code: number | null;
	stderr: string;
}

export class Sidecar {
	private child: ChildProcess | null = null;
	private stderr = "";
	private readonly exitHandlers: Array<(exit: BackendExit) => void> = [];

	start(binPath: string, port: number): void {
		const child = spawn(binPath, ["--port", String(port)], {
			stdio: ["ignore", "pipe", "pipe"],
		});
		this.child = child;
		child.stderr?.on("data", (chunk: Buffer) => {
			this.stderr = (this.stderr + chunk.toString()).slice(-STDERR_CAP);
		});
		child.on("exit", (code) => {
			const exit: BackendExit = { code, stderr: this.stderr.trim() };
			for (const handler of this.exitHandlers) {
				handler(exit);
			}
		});
	}

	onExit(handler: (exit: BackendExit) => void): void {
		this.exitHandlers.push(handler);
	}

	kill(): void {
		this.child?.kill();
		this.child = null;
	}
}
