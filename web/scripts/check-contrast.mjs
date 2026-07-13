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
	["--destructive", "--background"],
	["--destructive", "--card"],
	["--footer-foreground", "--footer"],
	["--footer-muted", "--footer"],
	// Новое: текст поверх акцентных плашек и красной плиты рисков. Жёлтая плашка —
	// главный кандидат на провал: на ней читаемым остаётся только тёмный текст.
	["--accent-ink", "--accent-1"],
	["--primary-foreground", "--accent-2"],
	["--background", "--destructive"],
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

/** Полярный OKLCH → прямоугольный OKLab (то, что color-mix(in oklab, ...) реально интерполирует). */
function oklchToOklab({ L, C, h }) {
	const hr = (h * Math.PI) / 180;
	return { L, a: C * Math.cos(hr), b: C * Math.sin(hr) };
}

function oklabToLinearSrgb({ L, a, b }) {
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

function oklchToSrgb(oklch) {
	return oklabToLinearSrgb(oklchToOklab(oklch));
}

/** color-mix(in oklab, A pctA%, B) — линейная интерполяция L/a/b компонент. */
function mixOklab(strA, pctA, strB) {
	const a = oklchToOklab(parseOklch(strA));
	const b = oklchToOklab(parseOklch(strB));
	const t = pctA / 100;
	return {
		L: a.L * t + b.L * (1 - t),
		a: a.a * t + b.a * (1 - t),
		b: a.b * t + b.b * (1 - t),
	};
}

/** Линейный sRGB → относительная яркость (WCAG). Клампим вне гаммы. */
function luminance(linear) {
	const [r, g, b] = linear.map((v) => Math.min(1, Math.max(0, v)));
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function luminanceOfOklch(str) {
	return luminance(oklchToSrgb(parseOklch(str)));
}

function luminanceOfOklab(oklab) {
	return luminance(oklabToLinearSrgb(oklab));
}

function contrastRatio(l1, l2) {
	const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
	return (hi + 0.05) / (lo + 0.05);
}

function ratio(fg, bg) {
	return contrastRatio(luminanceOfOklch(fg), luminanceOfOklch(bg));
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

	// .surface-recessed не токен, а вычисляемая заливка: color-mix(in oklab, var(--muted) 55%, var(--background)).
	// Эйрбоу (.label-mono.text-brand) сидит на ней в каждой muted-секции — гейт обязан это видеть.
	const recessed = mixOklab(tokens["--muted"], 55, tokens["--background"]);
	const rRecessed = contrastRatio(
		luminanceOfOklch(tokens["--brand"]),
		luminanceOfOklab(recessed),
	);
	const okRecessed = rRecessed >= 4.5;
	if (!okRecessed) failed = true;
	console.log(
		`${okRecessed ? "✓" : "✗"} ${theme.padEnd(5)} --brand на surface-recessed: ${rRecessed.toFixed(2)}:1`,
	);
}

if (failed) {
	console.error("\nКонтраст ниже AA (4.5:1). Правь токены в globals.css.");
	process.exit(1);
}
console.log("\nВсе пары держат AA.");
