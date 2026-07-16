import { API } from "$lib/api/client";
import type { SetupState } from "$lib/api/types";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SetupViewModel } from "./setup.viewmodel.svelte";

vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug() {},
		info() {},
		warn() {},
		error() {},
	}),
}));
vi.mock("$lib/api/client", () => ({
	API: {
		setup: {
			state: vi.fn(),
			local: vi.fn(),
			cloudModels: vi.fn(),
			pull: vi.fn(),
			trial: vi.fn(),
			deployment: vi.fn(),
		},
	},
}));

function state(overrides: Partial<SetupState> = {}): SetupState {
	return {
		hardware: { tier: "capable", ram_gb: 32, cores: 16 },
		ollama: "ready",
		has_deployment: false,
		local_model: "ollama_chat/qwen2.5:7b",
		cloud_model: "gigachat/GigaChat-2",
		claude_available: false,
		...overrides,
	};
}

beforeEach(() => vi.clearAllMocks());

describe("SetupViewModel (top level)", () => {
	it("starts on the choose screen even when a deployment already exists", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ has_deployment: true }),
		);
		const vm = new SetupViewModel();
		await vm.init();
		expect(vm.path).toBe("choose");
	});

	it("flags weak hardware for the local card", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ hardware: { tier: "weak", ram_gb: 8, cores: 4 } }),
		);
		const vm = new SetupViewModel();
		await vm.init();
		expect(vm.hardwareWeak).toBe(true);
	});

	it("enters the local branch and refreshes it", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(state());
		vi.mocked(API.setup.local).mockResolvedValue({
			ollama_state: "ready",
			installed_models: ["qwen2.5:7b"],
			recommended_tag: "qwen2.5:7b",
			recommended_installed: true,
		});
		const vm = new SetupViewModel();
		await vm.init();
		await vm.chooseLocal();
		expect(vm.path).toBe("local");
		expect(vm.local.screen).toBe("local-select");
	});

	it("enters the cloud branch and loads the catalog", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(state());
		vi.mocked(API.setup.cloudModels).mockResolvedValue([
			{
				model: "openai/gpt-4o",
				label: "gpt-4o",
				provider: "openai",
				key_url: "https://o",
			},
		]);
		const vm = new SetupViewModel();
		await vm.init();
		await vm.chooseCloud();
		expect(vm.path).toBe("cloud");
		expect(vm.cloud.screen).toBe("select");
	});

	it("passes the cache-sync callback down to both branches", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(state());
		vi.mocked(API.setup.cloudModels).mockResolvedValue([
			{
				model: "openai/gpt-4o",
				label: "gpt-4o",
				provider: "openai",
				key_url: "https://o",
			},
		]);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 4,
			letter: "ok",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const saved = vi.fn();
		const vm = new SetupViewModel(saved);
		await vm.init();
		await vm.chooseCloud();
		vm.cloud.choose(vm.cloud.models[0]);
		await vm.cloud.submitKey("sk");
		expect(saved).toHaveBeenCalledOnce();
	});
});
