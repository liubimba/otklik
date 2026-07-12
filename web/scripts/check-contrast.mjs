// Проверяет контраст токенов по формуле WCAG 2.1 — расчётом, а не на глаз.
// Запуск: npm run check:contrast
import { readFileSync } from "node:fs";

const CSS = readFileSync(
	new URL("../src/app/globals.css", import.meta.url),
	"utf8",
);

/** Пары «текст на фоне», которые обязаны держать AA (4.5:1). */
const PAIRS = [
	["--foreground", "--background"],
	["--muted-foreground", "--background"],
	["--muted-foreground", "--muted"],
	["--card-foreground", "--card"],
	["--primary-foreground", "--primary"],
	["--brand", "--background"],
];

function block(name) {
	// :root { ... } или .dark { ... }
	const re = new RegExp(`${name}\\s*\\{([\\s\\S]*?)\\n\\}`, "m");
	const m = CSS.match(re);
	if (!m) throw new Error(`Не найден блок ${name} в globals.css`);
	const tokens = {};
	for (const line of m[1].split("\n")) {
		const t = line.match(/(--[\w-]+):\s*(oklch\([^)]*\))/);
		if (t) tokens[t[1]] = t[2];
	}
	return tokens;
}

function parseOklch(str) {
	const m = str.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)/);
	if (!m) throw new Error(`Не разобрал цвет: ${str}`);
	return { L: +m[1], C: +m[2], h: +m[3] };
}

function oklchToSrgb({ L, C, h }) {
	const hr = (h * Math.PI) / 180;
	const a = C * Math.cos(hr);
	const b = C * Math.sin(hr);

	const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
	const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
	const s_ = L - 0.0894841775 * a - 1.291485548 * b;

	const l = l_ ** 3;
	const m = m_ ** 3;
	const s = s_ ** 3;

	return [
		+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
		-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
		-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
	];
}

/** Линейный sRGB → относительная яркость (WCAG). Клампим вне гаммы. */
function luminance(linear) {
	const [r, g, b] = linear.map((v) => Math.min(1, Math.max(0, v)));
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(fg, bg) {
	const l1 = luminance(oklchToSrgb(parseOklch(fg)));
	const l2 = luminance(oklchToSrgb(parseOklch(bg)));
	const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
	return (hi + 0.05) / (lo + 0.05);
}

const themes = { light: block(":root"), dark: block("\\.dark") };
let failed = false;

for (const [theme, tokens] of Object.entries(themes)) {
	for (const [fg, bg] of PAIRS) {
		if (!tokens[fg] || !tokens[bg]) {
			console.error(`✗ ${theme}: нет токена ${!tokens[fg] ? fg : bg}`);
			failed = true;
			continue;
		}
		const r = ratio(tokens[fg], tokens[bg]);
		const ok = r >= 4.5;
		if (!ok) failed = true;
		console.log(
			`${ok ? "✓" : "✗"} ${theme.padEnd(5)} ${fg} на ${bg}: ${r.toFixed(2)}:1`,
		);
	}
}

if (failed) {
	console.error("\nКонтраст ниже AA (4.5:1). Правь токены в globals.css.");
	process.exit(1);
}
console.log("\nВсе пары держат AA.");
