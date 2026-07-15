import { API } from "$lib/api/client";
import type { LocalSetupState } from "$lib/api/types";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocalFlow } from "./local-flow.svelte";

vi.mock("$lib/log", () => ({
	getLogger: () => ({ debug() {}, info() {}, warn() {}, error() {} }),
}));
vi.mock("$lib/api/client", () => ({
	API: {
		setup: {
			local: vi.fn(),
			pull: vi.fn(),
			trial: vi.fn(),
			deployment: vi.fn(),
		},
	},
}));

function local(overrides: Partial<LocalSetupState> = {}): LocalSetupState {
	return {
		ollama_state: "ready",
		installed_models: ["qwen2.5:7b", "llama3:8b"],
		recommended_tag: "qwen2.5:7b",
		recommended_installed: true,
		...overrides,
	};
}

beforeEach(() => vi.clearAllMocks());

describe("LocalFlow", () => {
	it("shows the installed model list when Ollama is ready", async () => {
		vi.mocked(API.setup.local).mockResolvedValue(local());
		const flow = new LocalFlow(() => {});
		await flow.refresh();
		expect(flow.screen).toBe("local-select");
		expect(flow.installedModels).toEqual(["qwen2.5:7b", "llama3:8b"]);
	});

	it("benchmarks the chosen installed model and writes it primary on pass", async () => {
		vi.mocked(API.setup.local).mockResolvedValue(local());
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 6,
			letter: "Здравствуйте!",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const saved = vi.fn();
		const flow = new LocalFlow(saved);
		await flow.refresh();
		await flow.selectInstalled("llama3:8b");
		expect(flow.screen).toBe("done");
		expect(API.setup.trial).toHaveBeenCalledWith(
			{
				model: "ollama_chat/llama3:8b",
				api_base: "http://localhost:11434",
				api_key: null,
			},
			45,
		);
		expect(API.setup.deployment).toHaveBeenCalledWith({
			model: "ollama_chat/llama3:8b",
			api_base: "http://localhost:11434",
			api_key: null,
		});
		expect(saved).toHaveBeenCalledOnce();
	});

	it("routes a deadline to the too-slow fork without writing a deployment", async () => {
		vi.mocked(API.setup.local).mockResolvedValue(local());
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: false,
			seconds: 45,
			letter: null,
			failure_reason: "deadline",
			error: null,
		});
		const flow = new LocalFlow(() => {});
		await flow.refresh();
		await flow.selectInstalled("qwen2.5:7b");
		expect(flow.screen).toBe("too-slow");
		expect(API.setup.deployment).not.toHaveBeenCalled();
	});

	it("pulls the recommended model then benchmarks it", async () => {
		vi.mocked(API.setup.local).mockResolvedValue(
			local({ installed_models: [], recommended_installed: false }),
		);
		async function* prog() {
			yield {
				status: "success",
				completed_bytes: 100,
				total_bytes: 100,
				percent: 100,
				done: true,
			};
		}
		vi.mocked(API.setup.pull).mockReturnValue(prog() as never);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 6,
			letter: "ok",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const flow = new LocalFlow(() => {});
		await flow.refresh();
		await flow.installRecommended();
		expect(flow.percent).toBe(100);
		expect(flow.screen).toBe("done");
		expect(API.setup.trial).toHaveBeenCalledWith(
			{
				model: "ollama_chat/qwen2.5:7b",
				api_base: "http://localhost:11434",
				api_key: null,
			},
			45,
		);
	});

	it("routes a model error to the error screen, not the 'too slow' fork", async () => {
		// P0: a model that never answered (crash/OOM/refused connection) must
		// not be offered as "slow but keepable" — the user would pick "keep
		// local" on a deployment that has never once produced a letter.
		vi.mocked(API.setup.local).mockResolvedValue(local());
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: false,
			seconds: 0.3,
			letter: null,
			failure_reason: "model_error",
			error: "connection refused",
		});
		const flow = new LocalFlow(() => {});
		await flow.refresh();
		await flow.selectInstalled("qwen2.5:7b");
		expect(flow.screen).toBe("error");
		expect(flow.errorMessage).toContain("connection refused");
		expect(API.setup.deployment).not.toHaveBeenCalled();
	});

	it("never gets a chance to write a deployment for a model that never answered", async () => {
		// selectInstalled()/installRecommended() must never land on "too-slow"
		// for a model_error — only a real deadline failure is a keepable fork.
		vi.mocked(API.setup.local).mockResolvedValue(local());
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: false,
			seconds: 0.1,
			letter: null,
			failure_reason: "model_error",
			error: "model 'qwen2.5:7b' not found, try pulling it first",
		});
		const flow = new LocalFlow(() => {});
		await flow.refresh();
		await flow.selectInstalled("qwen2.5:7b");
		expect(flow.screen).not.toBe("too-slow");
		expect(flow.screen).toBe("error");
	});

	it("surfaces a pull failure instead of hanging on the progress bar", async () => {
		vi.mocked(API.setup.local).mockResolvedValue(
			local({ installed_models: [], recommended_installed: false }),
		);
		vi.mocked(API.setup.pull).mockImplementation(() => {
			throw new Error("no space left on device");
		});
		const flow = new LocalFlow(() => {});
		await flow.refresh();
		await flow.installRecommended();
		expect(flow.screen).toBe("error");
		expect(flow.errorMessage).toContain("no space left on device");
		expect(API.setup.deployment).not.toHaveBeenCalled();
	});

	it("maps ollama states to their screens", async () => {
		for (const [state, screen] of [
			["not_installed", "ollama-missing"],
			["not_running", "ollama-stopped"],
		] as const) {
			vi.mocked(API.setup.local).mockResolvedValue(
				local({ ollama_state: state }),
			);
			const flow = new LocalFlow(() => {});
			await flow.refresh();
			expect(flow.screen).toBe(screen);
		}
	});
});
