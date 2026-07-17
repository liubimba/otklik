// @vitest-environment node
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolveConfig } from "vite";
import { afterEach, describe, expect, it } from "vitest";

const configDir = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"../..",
);

async function resolveClientConditions(): Promise<readonly string[]> {
	const saved = process.env.VITEST;
	// biome-ignore lint/performance/noDelete: автофикс "= undefined" даёт truthy строку "undefined"
	delete process.env.VITEST;
	try {
		const config = await resolveConfig(
			{ configFile: path.join(configDir, "vite.config.js"), root: configDir },
			"build",
			"production",
			"production",
		);
		return config.environments.client.resolve.conditions;
	} finally {
		if (saved !== undefined) process.env.VITEST = saved;
	}
}

afterEach(() => {
	expect(process.env.VITEST).toBeDefined();
});

describe("vite.config.js — условия резолва клиентского бандла", () => {
	it("сохраняет 'browser', иначе svelte резолвится на серверную сборку", async () => {
		expect(await resolveClientConditions()).toContain("browser");
	});

	it("не теряет остальные дефолты вайта", async () => {
		const conditions = await resolveClientConditions();
		expect(conditions).toContain("module");
		expect(conditions).toContain("development|production");
	});

	it("добавляет 'svelte' — ради exports-мап formsnap/svelte-toolbelt", async () => {
		expect(await resolveClientConditions()).toContain("svelte");
	});
});
