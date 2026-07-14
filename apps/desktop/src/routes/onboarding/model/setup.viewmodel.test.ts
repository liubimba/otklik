import { API } from "$lib/api/client";
import type { PullProgress, SetupState } from "$lib/api/types";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SetupViewModel } from "./setup.viewmodel.svelte";

// Тестовое окружение не под Tauri: без мока реальный логгер лезет в
// `@tauri-apps/plugin-log` и роняет прогон необработанным rejection'ом.
vi.mock("$lib/log", () => ({
	getLogger: () => ({
		debug: () => {},
		info: () => {},
		warn: () => {},
		error: () => {},
	}),
}));

vi.mock("$lib/api/client", () => ({
	API: {
		setup: {
			state: vi.fn(),
			pull: vi.fn(),
			benchmark: vi.fn(),
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
		...overrides,
	};
}

async function* progress(...percents: number[]): AsyncGenerator<PullProgress> {
	for (const percent of percents) {
		yield {
			status: percent === 100 ? "success" : "downloading",
			completed_bytes: percent,
			total_bytes: 100,
			percent,
			done: percent === 100,
		};
	}
}

beforeEach(() => vi.clearAllMocks());

describe("SetupViewModel", () => {
	it("skips the whole step when a deployment already exists", async () => {
		// P0-1: повторное прохождение онбординга не должно снова гонять замер
		// и качать модель — она уже настроена.
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ has_deployment: true }),
		);
		const vm = new SetupViewModel();

		await vm.refresh();

		expect(vm.screen).toBe("done");
		expect(API.setup.benchmark).not.toHaveBeenCalled();
		expect(API.setup.pull).not.toHaveBeenCalled();
	});

	it("sends a weak machine to the fork, without downloading anything", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ hardware: { tier: "weak", ram_gb: 8, cores: 4 } }),
		);
		const vm = new SetupViewModel();

		await vm.refresh();

		expect(vm.screen).toBe("weak-hardware");
		expect(API.setup.pull).not.toHaveBeenCalled();
	});

	it("asks to install Ollama when it is absent", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ ollama: "not_installed" }),
		);
		const vm = new SetupViewModel();

		await vm.refresh();

		expect(vm.screen).toBe("ollama-missing");
	});

	it("asks to start Ollama when it is installed but silent", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ ollama: "not_running" }),
		);
		const vm = new SetupViewModel();

		await vm.refresh();

		expect(vm.screen).toBe("ollama-stopped");
	});

	it("offers the pull when the model is missing", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ ollama: "model_missing" }),
		);
		const vm = new SetupViewModel();

		await vm.refresh();

		expect(vm.screen).toBe("pull");
		expect(vm.percent).toBe(0);
	});

	it("tracks real pull percentages and moves on to the benchmark", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ ollama: "model_missing" }),
		);
		vi.mocked(API.setup.pull).mockReturnValue(progress(25, 100));
		vi.mocked(API.setup.benchmark).mockResolvedValue({
			passed: true,
			seconds: 6.1,
			letter: "Здравствуйте!",
		});
		const vm = new SetupViewModel();
		await vm.refresh();

		await vm.pullModel();

		expect(vm.percent).toBe(100);
		expect(vm.screen).toBe("done");
		expect(API.setup.deployment).toHaveBeenCalledWith({
			model: "ollama_chat/qwen2.5:7b",
			api_base: "http://localhost:11434",
			api_key: null,
		});
	});

	it("shows the letter the machine wrote", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(state());
		vi.mocked(API.setup.benchmark).mockResolvedValue({
			passed: true,
			seconds: 6.1,
			letter: "Здравствуйте! Меня заинтересовала вакансия.",
		});
		const vm = new SetupViewModel();
		await vm.refresh();

		await vm.runBenchmark();

		expect(vm.screen).toBe("done");
		expect(vm.letter).toContain("Здравствуйте");
		expect(vm.seconds).toBe(6.1);
	});

	it("does not write the deployment when the machine is too slow", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(state());
		vi.mocked(API.setup.benchmark).mockResolvedValue({
			passed: false,
			seconds: 45,
			letter: null,
		});
		const vm = new SetupViewModel();
		await vm.refresh();

		await vm.runBenchmark();

		expect(vm.screen).toBe("too-slow");
		expect(API.setup.deployment).not.toHaveBeenCalled();
	});

	it("writes the deployment when the user keeps the slow local model", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(state());
		vi.mocked(API.setup.benchmark).mockResolvedValue({
			passed: false,
			seconds: 45,
			letter: null,
		});
		const vm = new SetupViewModel();
		await vm.refresh();
		await vm.runBenchmark();

		await vm.keepLocal();

		expect(API.setup.deployment).toHaveBeenCalledOnce();
		expect(vm.screen).toBe("done");
	});

	it("surfaces a pull failure instead of hanging on the progress bar", async () => {
		vi.mocked(API.setup.state).mockResolvedValue(
			state({ ollama: "model_missing" }),
		);
		vi.mocked(API.setup.pull).mockImplementation(() => {
			throw new Error("no space left on device");
		});
		const vm = new SetupViewModel();
		await vm.refresh();

		await vm.pullModel();

		expect(vm.screen).toBe("error");
		expect(vm.errorMessage).toContain("no space left on device");
	});
});
