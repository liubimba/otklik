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
// зелёными на полностью сломанном dev/prod. Механика ровно такая: во время
// настоящего прогона плагин самого vitest подмешивает в конфиг
// resolve.conditions: ["node"], и только тогда addBrowserCondition() из
// @testing-library/svelte находит "node" и вставляет "browser" перед ним
// (см. его vite.js: splice происходит ТОЛЬКО если "node" уже в списке).
// Компонентные тесты жили в условиях резолва, не совпадающих ни с dev, ни с
// build, — и потому к этому классу поломок слепы структурно.
//
// Этот тест зовёт resolveConfig() напрямую, мимо плагина vitest: "node" в
// список не попадает, значит и addBrowserCondition ничего не вставляет, значит
// условия видны ровно такими, какими их получит `pnpm build`. Именно поэтому
// гейт работает.
//
// ВАЖНО про охват: тест проверяет ПРОКСИ (массив conditions), а не исход (что
// svelte резолвится в index-client.js). Он не поймает поломку через
// resolve.alias, mainFields, dedupe или optimizeDeps, и щупает только
// command: "build" (сегодня идентичен "serve"). Это точечный гейт на одну
// регрессию, а не покрытие клиентского резолва вообще.
const configDir = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"../..",
);

async function resolveClientConditions(): Promise<readonly string[]> {
	const saved = process.env.VITEST;
	// Страховка, а НЕ несущая конструкция: сегодня VITEST на условия резолва не
	// влияет вовсе (проверено — с ним и без него resolveConfig отдаёт
	// одинаковый список), потому что svelteTesting() вставляет "browser" только
	// при уже присутствующем "node", а его сюда кладёт плагин vitest, которого
	// в прямом вызове resolveConfig нет. Снимаем на случай, если
	// @testing-library/svelte однажды начнёт добавлять "browser" безусловно —
	// тогда тест молча перестал бы что-либо проверять. Цена — одна строка.
	//
	// Именно delete, а не автофикс биома (= undefined): process.env приводит
	// значение к строке, переменная стала бы "undefined" — truthy, то есть
	// «снятие» ничего бы не сняло.
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
