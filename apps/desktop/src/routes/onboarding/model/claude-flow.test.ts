import { API } from "$lib/api/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ClaudeFlow } from "./claude-flow.svelte";

vi.mock("$lib/log", () => ({
	getLogger: () => ({ debug() {}, info() {}, warn() {}, error() {} }),
}));
vi.mock("$lib/api/client", () => ({
	API: { setup: { claude: vi.fn(), trial: vi.fn(), deployment: vi.fn() } },
}));

const READY = {
	claude_state: "ready",
	default_model: "claude-code/sonnet",
	model_options: [
		{ model: "claude-code/sonnet", label: "Claude Sonnet" },
		{ model: "claude-code/opus", label: "Claude Opus" },
		{ model: "claude-code/haiku", label: "Claude Haiku" },
	],
};

beforeEach(() => vi.clearAllMocks());

describe("ClaudeFlow", () => {
	it("lands on select with the default model when ready", async () => {
		vi.mocked(API.setup.claude).mockResolvedValue(READY as never);
		const flow = new ClaudeFlow(() => {});
		await flow.load();
		expect(flow.screen).toBe("select");
		expect(flow.selected).toBe("claude-code/sonnet");
		expect(flow.models).toHaveLength(3);
	});

	it("routes to not-installed / not-authed by gate state", async () => {
		vi.mocked(API.setup.claude).mockResolvedValue({
			...READY,
			claude_state: "not_installed",
		} as never);
		const a = new ClaudeFlow(() => {});
		await a.load();
		expect(a.screen).toBe("not-installed");

		vi.mocked(API.setup.claude).mockResolvedValue({
			...READY,
			claude_state: "not_authed",
		} as never);
		const b = new ClaudeFlow(() => {});
		await b.load();
		expect(b.screen).toBe("not-authed");
	});

	it("writes the deployment only after a successful trial", async () => {
		vi.mocked(API.setup.claude).mockResolvedValue(READY as never);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 8,
			letter: "Здравствуйте!",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const saved = vi.fn();
		const flow = new ClaudeFlow(saved);
		await flow.load();
		flow.selectModel("claude-code/opus");
		const ok = await flow.runTrial();
		expect(ok).toBe(true);
		expect(API.setup.trial).toHaveBeenCalledWith(
			{ model: "claude-code/opus", api_key: null, api_base: null },
			90,
		);
		expect(API.setup.deployment).toHaveBeenCalledWith({
			model: "claude-code/opus",
			api_key: null,
			api_base: null,
		});
		expect(saved).toHaveBeenCalledOnce();
	});

	it("stays on select with an error when the trial fails, writing nothing", async () => {
		vi.mocked(API.setup.claude).mockResolvedValue(READY as never);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: false,
			seconds: 3,
			letter: null,
			failure_reason: "model_error",
			error: "not logged in",
		});
		const flow = new ClaudeFlow(() => {});
		await flow.load();
		const ok = await flow.runTrial();
		expect(ok).toBe(false);
		expect(flow.screen).toBe("select");
		expect(flow.errorMessage).toContain("not logged in");
		expect(API.setup.deployment).not.toHaveBeenCalled();
	});

	it("guards against a concurrent double-submit", async () => {
		vi.mocked(API.setup.claude).mockResolvedValue(READY as never);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 8,
			letter: "ok",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const flow = new ClaudeFlow(() => {});
		await flow.load();
		const [a, b] = await Promise.all([flow.runTrial(), flow.runTrial()]);
		expect(a).toBe(true);
		expect(b).toBe(false);
		expect(API.setup.trial).toHaveBeenCalledOnce();
	});
});
