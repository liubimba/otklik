import { API } from "$lib/api/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CloudFlow } from "./cloud-flow.svelte";

vi.mock("$lib/log", () => ({
	getLogger: () => ({ debug() {}, info() {}, warn() {}, error() {} }),
}));
vi.mock("$lib/api/client", () => ({
	API: { setup: { cloudModels: vi.fn(), trial: vi.fn(), deployment: vi.fn() } },
}));

const OPTIONS = [
	{
		model: "openai/gpt-4o",
		label: "gpt-4o",
		provider: "openai",
		key_url: "https://o",
	},
	{
		model: "anthropic/claude-3-5-sonnet",
		label: "claude-3-5-sonnet",
		provider: "anthropic",
		key_url: "https://a",
	},
];

beforeEach(() => vi.clearAllMocks());

describe("CloudFlow", () => {
	it("loads the catalog and lands on select", async () => {
		vi.mocked(API.setup.cloudModels).mockResolvedValue(OPTIONS);
		const flow = new CloudFlow(() => {});
		await flow.load();
		expect(flow.screen).toBe("select");
		expect(flow.models).toHaveLength(2);
	});

	it("filters by substring over label and provider", async () => {
		vi.mocked(API.setup.cloudModels).mockResolvedValue(OPTIONS);
		const flow = new CloudFlow(() => {});
		await flow.load();
		flow.setQuery("claude");
		expect(flow.filtered.map((o) => o.model)).toEqual([
			"anthropic/claude-3-5-sonnet",
		]);
		flow.setQuery("openai");
		expect(flow.filtered.map((o) => o.model)).toEqual(["openai/gpt-4o"]);
	});

	it("writes the deployment only after a successful trial", async () => {
		vi.mocked(API.setup.cloudModels).mockResolvedValue(OPTIONS);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 4,
			letter: "Здравствуйте!",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const saved = vi.fn();
		const flow = new CloudFlow(saved);
		await flow.load();
		flow.choose(OPTIONS[0]);
		expect(flow.screen).toBe("key");
		const ok = await flow.submitKey("sk-123");
		expect(ok).toBe(true);
		expect(flow.letter).toContain("Здравствуйте");
		expect(API.setup.trial).toHaveBeenCalledWith(
			{ model: "openai/gpt-4o", api_key: "sk-123" },
			60,
		);
		expect(API.setup.deployment).toHaveBeenCalledWith({
			model: "openai/gpt-4o",
			api_key: "sk-123",
		});
		expect(saved).toHaveBeenCalledOnce();
	});

	it("guards against a concurrent double-submit", async () => {
		vi.mocked(API.setup.cloudModels).mockResolvedValue(OPTIONS);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: true,
			seconds: 4,
			letter: "Здравствуйте!",
			failure_reason: null,
			error: null,
		});
		vi.mocked(API.setup.deployment).mockResolvedValue({
			llm: { deployments: [] },
		} as never);
		const flow = new CloudFlow(() => {});
		await flow.load();
		flow.choose(OPTIONS[0]);

		const first = flow.submitKey("sk-123");
		const second = flow.submitKey("sk-123");
		const [firstResult, secondResult] = await Promise.all([first, second]);

		expect(firstResult).toBe(true);
		expect(secondResult).toBe(false);
		expect(API.setup.trial).toHaveBeenCalledOnce();
		expect(API.setup.deployment).toHaveBeenCalledOnce();
	});

	it("stays on key with an error when the trial fails, and never writes a deployment", async () => {
		vi.mocked(API.setup.cloudModels).mockResolvedValue(OPTIONS);
		vi.mocked(API.setup.trial).mockResolvedValue({
			passed: false,
			seconds: 2,
			letter: null,
			failure_reason: "model_error",
			error: "invalid api key",
		});
		const flow = new CloudFlow(() => {});
		await flow.load();
		flow.choose(OPTIONS[0]);
		const ok = await flow.submitKey("bad");
		expect(ok).toBe(false);
		expect(flow.screen).toBe("key");
		expect(flow.errorMessage).toContain("invalid api key");
		expect(API.setup.deployment).not.toHaveBeenCalled();
	});
});
