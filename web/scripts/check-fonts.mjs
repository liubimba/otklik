// Проверяет, что каждый подключённый шрифт реально имеет кириллицу.
// Русский заголовок в шрифте без кириллицы молча падает на системный.
// Запуск: npm run check:fonts
import { readFileSync } from "node:fs";

const LAYOUT = readFileSync(
	new URL("../src/app/layout.tsx", import.meta.url),
	"utf8",
);

// import { Geologica, Golos_Text, JetBrains_Mono } from "next/font/google";
const importLine = LAYOUT.match(
	/import\s*\{([^}]+)\}\s*from\s*"next\/font\/google"/,
);
if (!importLine) {
	console.error("✗ В layout.tsx нет импорта из next/font/google");
	process.exit(1);
}

const families = importLine[1]
	.split(",")
	.map((s) => s.trim())
	.filter(Boolean);

const UA =
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36";

let failed = false;

for (const family of families) {
	const query = family.replace(/_/g, "+"); // Golos_Text -> Golos+Text
	const url = `https://fonts.googleapis.com/css2?family=${query}:wght@400&display=swap`;
	const res = await fetch(url, { headers: { "User-Agent": UA } });
	const css = await res.text();

	const hasCyrillic = css.includes("/* cyrillic */");
	if (!hasCyrillic) failed = true;
	console.log(`${hasCyrillic ? "✓" : "✗"} ${family.replace(/_/g, " ")}`);

	// Шрифт подключён — значит в layout.tsx у него обязан стоять subset.
	const declared = new RegExp(
		`${family}\\(\\{[^}]*subsets:\\s*\\[[^\\]]*"cyrillic"`,
		"s",
	).test(LAYOUT);
	if (!declared) {
		failed = true;
		console.error(
			`  ✗ ${family}: в layout.tsx не указан subsets: [..., "cyrillic"]`,
		);
	}
}

if (failed) {
	console.error("\nЕсть шрифт без кириллицы или без объявленного subset.");
	process.exit(1);
}
console.log("\nВсе шрифты несут кириллицу.");
