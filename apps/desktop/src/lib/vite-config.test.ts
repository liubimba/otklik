// @vitest-environment node
//
// Не jsdom: resolveConfig() поднимает esbuild, а тот отказывается работать под
// jsdom (его TextEncoder отдаёт не настоящий Uint8Array). Тесту DOM и не нужен —
// он читает конфиг, а не рендерит.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolveConfig } from "vite";
import { afterEach, describe, expect, it } from "vitest";

// Гейт на саму конфигурацию сборки, а не на код приложения.
//
// Зачем: resolve.conditions ЗАМЕЩАЕТ дефолты вайта, а не дополняет их. Стоило
// написать conditions: ["svelte"] — и из клиентских условий пропадал "browser",
// после чего svelte резолвился по ветке "default" своей exports-мапы, то есть
// на СЕРВЕРНУЮ сборку. В приложении это означало: onDestroy падает на любой
// странице с superForm (Настройки), onMount тихо становится no-op'ом,
// svelte/reactivity подменяется нереактивными заглушками внутри bits-ui/runed,
// untrack вырождается в (fn) => fn().
//
// И ни один гейт этого не ловил: vitest, pnpm check и pnpm build оставались
// зелёными на полностью сломанном dev/prod. Потому что svelteTesting() из
// @testing-library/svelte возвращает "browser" обратно — но ровно тогда, когда
// выставлен process.env.VITEST. Тесты чинили окружение под собой и слепли к
// поломке, которую видел бы только живой запуск.
//
// Поэтому тест снимает VITEST на время резолва: он обязан видеть конфиг ровно
// таким, каким его получит `pnpm tauri dev` и `pnpm build`.
const configDir = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"../..",
);

async function resolveClientConditions(): Promise<readonly string[]> {
	const saved = process.env.VITEST;
	// Только delete: автофикс биома (= undefined) здесь НЕВЕРЕН — process.env
	// приводит значение к строке, переменная стала бы "undefined", то есть
	// truthy. Проверка `if (!process.env.VITEST) return` внутри svelteTesting()
	// всё равно вернула бы "browser", и тест перестал бы ловить ровно то, ради
	// чего написан.
	// biome-ignore lint/performance/noDelete: см. комментарий выше
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
	expect(process.env.VITEST).toBeDefined(); // страховка: env восстановлен
});

describe("vite.config.js — условия резолва клиентского бандла", () => {
	it("сохраняет 'browser', иначе svelte резолвится на серверную сборку", async () => {
		expect(await resolveClientConditions()).toContain("browser");
	});

	it("не теряет остальные дефолты вайта", async () => {
		const conditions = await resolveClientConditions();
		// Ровно те, что вайт кладёт в defaultClientConditions. Если добавляете
		// своё условие — спредом, а не заменой.
		expect(conditions).toContain("module");
		expect(conditions).toContain("development|production");
	});

	it("добавляет 'svelte' — ради exports-мап formsnap/svelte-toolbelt", async () => {
		// Причина, по которой условие вообще прописано статически: приватная
		// копия vite внутри @vitest/mocker не получает его от vite-plugin-svelte.
		expect(await resolveClientConditions()).toContain("svelte");
	});
});
