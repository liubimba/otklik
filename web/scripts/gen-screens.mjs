// Генератор SVG-заглушек «Как это работает» под текущую палитру.
// Геометрия (viewBox 1248×765, шапка 44px, сайдбар 232px, панели/ряды) —
// перенесена из прежних вручную нарисованных SVG без изменений.
// Меняются только цвета: они выведены из токенов Задачи 3 (globals.css).
//
// Запуск: npm run gen:screens

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = join(__dirname, "..", "public");
const SCREENS_DIR = join(PUBLIC_DIR, "screens");

const W = 1248;
const H = 765;

// sRGB-эквиваленты токенов Task 3 (см. src/app/globals.css).
const DARK = {
	bg: "#1c1e24", // --background  oklch(0.15 0.012 255)
	bar: "#23262d",
	panel: "#23262d", // --card        oklch(0.19 0.012 255)
	sunken: "#1c1e24",
	line: "#5b606b", // --muted-foreground
	lineSoft: "#2b2f37", // --muted
	dot: "#3a3e47",
	brand: "#e2483a", // --brand (dark) oklch(0.62 0.2 28)
	brandSoft: "#4a2320",
	ok: "#1d4a33", // «Отправлено» — единственный зелёный на странице
	onBrand: "#fdece9",
	stroke: "none",
};

const LIGHT = {
	bg: "#fafbfc", // --background oklch(0.985 0.003 255)
	bar: "#f1f3f5",
	panel: "#ffffff", // --card
	sunken: "#ffffff",
	line: "#c9ccd3",
	lineSoft: "#f1f3f5", // --muted
	dot: "#c9ccd3",
	brand: "#c0361f", // --brand (light) = красный приложения
	brandSoft: "#fbe4e0",
	ok: "#dcf5e6",
	onBrand: "#ffffff",
	stroke: "#e3e6ea",
};

function svg(label, ...parts) {
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${label}">\n${parts.join("\n")}\n</svg>\n`;
}

function rect(x, y, w, h, fill, { rx = 0, stroke } = {}) {
	const strokeAttr = stroke ? ` stroke="${stroke}"` : "";
	return `  <rect x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ""} fill="${fill}"${strokeAttr}/>`;
}

function circle(cx, cy, r, fill) {
	return `  <circle cx="${cx}" cy="${cy}" r="${r}" fill="${fill}"/>`;
}

/** Полоска заголовка окна (мокап приложения): фон, три «трафик-лайта», заголовок. */
function titleBar(T) {
	return [
		rect(0, 0, W, H, T.bg),
		rect(0, 0, W, 44, T.bar),
		circle(24, 22, 6, T.dot),
		circle(44, 22, 6, T.dot),
		circle(64, 22, 6, T.dot),
		rect(576, 15, 96, 14, T.lineSoft, { rx: 7 }),
	].join("\n");
}

/** Четыре пункта меню сайдбара — общая раскладка для всех пяти шагов. */
const NAV_ROWS = [
	{ icon: 134, label: 133, labelW: 104 },
	{ icon: 182, label: 181, labelW: 84 },
	{ icon: 230, label: 229, labelW: 120 },
	{ icon: 278, label: 277, labelW: 68 },
];

/** Сайдбар шаговых экранов (не hero): лого, 4 пункта меню, карточка профиля. */
function sidebar(T, activeIndex) {
	const out = [
		rect(0, 44, 232, 721, T.panel, { stroke: T.stroke }),
		rect(24, 76, 88, 16, T.dot, { rx: 8 }),
	];
	NAV_ROWS.forEach((row, i) => {
		if (i === activeIndex) {
			out.push(rect(16, row.icon - 14, 200, 40, T.brandSoft, { rx: 10 }));
			out.push(rect(32, row.icon, 18, 12, T.brand, { rx: 4 }));
		} else {
			out.push(rect(32, row.icon, 18, 12, T.dot, { rx: 4 }));
		}
		out.push(rect(62, row.label, row.labelW, 14, T.dot, { rx: 7 }));
	});
	out.push(rect(16, 693, 200, 48, T.lineSoft, { rx: 10 }));
	out.push(circle(44, 717, 14, T.dot));
	out.push(rect(68, 711, 88, 12, T.dot, { rx: 6 }));
	return out.join("\n");
}

// ---------------------------------------------------------------------------
// Шаг 1 — вход в hh.ru
// ---------------------------------------------------------------------------
function stepAuth(T) {
	return svg(
		"Вход в аккаунт hh.ru в окне Otklik",
		titleBar(T),
		sidebar(T, 3),
		rect(256, 76, 960, 628, T.panel, { rx: 16, stroke: T.stroke }),
		"  <!-- окно логина -->",
		rect(420, 170, 632, 440, T.sunken, { rx: 16, stroke: T.stroke }),
		rect(420, 170, 632, 44, T.bar, { rx: 16 }),
		rect(444, 186, 120, 12, T.dot, { rx: 6 }),
		rect(468, 258, 180, 18, T.dot, { rx: 9 }),
		rect(468, 306, 536, 44, T.panel, { rx: 10, stroke: T.stroke }),
		rect(492, 320, 200, 12, T.dot, { rx: 6 }),
		rect(468, 366, 536, 44, T.panel, { rx: 10, stroke: T.stroke }),
		rect(492, 380, 160, 12, T.dot, { rx: 6 }),
		rect(468, 434, 536, 44, T.brand, { rx: 10 }),
		rect(676, 452, 120, 12, T.onBrand, { rx: 6 }),
		rect(468, 502, 280, 12, T.dot, { rx: 6 }),
	);
}

// ---------------------------------------------------------------------------
// Шаг 2 — настройки: резюме, стиль письма, LLM-провайдеры
// ---------------------------------------------------------------------------
function stepSettings(T) {
	return svg(
		"Настройки Otklik: резюме, стиль письма, LLM-провайдеры",
		titleBar(T),
		sidebar(T, 2),
		rect(256, 76, 140, 16, T.dot, { rx: 8 }),
		"  <!-- вкладки -->",
		rect(256, 112, 88, 32, T.brandSoft, { rx: 8 }),
		rect(276, 123, 48, 10, T.brand, { rx: 5 }),
		rect(352, 112, 88, 32, T.lineSoft, { rx: 8 }),
		rect(372, 123, 48, 10, T.dot, { rx: 5 }),
		rect(448, 112, 88, 32, T.lineSoft, { rx: 8 }),
		rect(468, 123, 48, 10, T.dot, { rx: 5 }),
		"  <!-- резюме -->",
		rect(256, 168, 960, 220, T.panel, { rx: 16, stroke: T.stroke }),
		rect(288, 196, 120, 14, T.dot, { rx: 7 }),
		rect(288, 228, 896, 132, T.sunken, { rx: 10, stroke: T.stroke }),
		rect(312, 252, 820, 10, T.dot, { rx: 5 }),
		rect(312, 276, 760, 10, T.dot, { rx: 5 }),
		rect(312, 300, 840, 10, T.dot, { rx: 5 }),
		rect(312, 324, 600, 10, T.dot, { rx: 5 }),
		"  <!-- LLM-провайдеры -->",
		rect(256, 408, 960, 296, T.panel, { rx: 16, stroke: T.stroke }),
		rect(288, 436, 180, 14, T.dot, { rx: 7 }),
		rect(288, 472, 896, 64, T.sunken, { rx: 10, stroke: T.stroke }),
		rect(312, 494, 16, 16, T.brand, { rx: 4 }),
		rect(344, 496, 240, 12, T.dot, { rx: 6 }),
		rect(1080, 494, 80, 20, T.ok, { rx: 10 }),
		rect(288, 552, 896, 64, T.sunken, { rx: 10, stroke: T.stroke }),
		rect(312, 574, 16, 16, T.dot, { rx: 4 }),
		rect(344, 576, 200, 12, T.dot, { rx: 6 }),
		rect(288, 632, 896, 48, T.sunken, { rx: 10, stroke: T.stroke }),
		rect(312, 650, 160, 12, T.dot, { rx: 6 }),
	);
}

// ---------------------------------------------------------------------------
// Шаг 3 — очередь вакансий со статусами
// ---------------------------------------------------------------------------
function queueRow(T, y, pillFill) {
	return [
		rect(256, y, 960, 92, T.panel, { rx: 16, stroke: T.stroke }),
		rect(288, y + 24, 280, 14, T.dot, { rx: 7 }),
		rect(288, y + 54, 180, 10, T.dot, { rx: 5 }),
		rect(1080, y + 34, 104, 24, pillFill, { rx: 12 }),
	].join("\n");
}

function stepSearch(T) {
	return svg(
		"Очередь вакансий Otklik с их статусами",
		titleBar(T),
		sidebar(T, 0),
		rect(256, 76, 180, 16, T.dot, { rx: 8 }),
		rect(1064, 72, 152, 40, T.brand, { rx: 10 }),
		rect(1104, 86, 72, 12, T.onBrand, { rx: 6 }),
		queueRow(T, 168, T.ok),
		queueRow(T, 276, T.ok),
		queueRow(T, 384, T.lineSoft),
		queueRow(T, 492, T.lineSoft),
		queueRow(T, 600, T.lineSoft),
	);
}

// ---------------------------------------------------------------------------
// Шаг 4 — разбор письма + AI-чат
// ---------------------------------------------------------------------------
function stepReview(T) {
	return svg(
		"Разбор сопроводительного письма и AI-чат в Otklik",
		titleBar(T),
		sidebar(T, 0),
		"  <!-- список слева, приглушён -->",
		rect(256, 76, 300, 628, T.panel, { rx: 16, stroke: T.stroke }),
		rect(280, 108, 200, 12, T.lineSoft, { rx: 6 }),
		rect(280, 140, 140, 12, T.lineSoft, { rx: 6 }),
		rect(280, 200, 220, 12, T.lineSoft, { rx: 6 }),
		rect(280, 232, 160, 12, T.lineSoft, { rx: 6 }),
		rect(280, 292, 180, 12, T.lineSoft, { rx: 6 }),
		rect(280, 324, 200, 12, T.lineSoft, { rx: 6 }),
		"  <!-- панель письма -->",
		rect(580, 76, 636, 628, T.panel, { rx: 16, stroke: T.stroke }),
		rect(612, 108, 220, 16, T.dot, { rx: 8 }),
		rect(612, 140, 300, 10, T.dot, { rx: 5 }),
		rect(612, 180, 572, 300, T.sunken, { rx: 10, stroke: T.stroke }),
		rect(636, 208, 520, 10, T.dot, { rx: 5 }),
		rect(636, 234, 480, 10, T.dot, { rx: 5 }),
		rect(636, 260, 524, 10, T.dot, { rx: 5 }),
		rect(636, 286, 440, 10, T.dot, { rx: 5 }),
		rect(636, 312, 500, 10, T.dot, { rx: 5 }),
		rect(636, 338, 300, 10, T.dot, { rx: 5 }),
		"  <!-- AI-чат -->",
		rect(612, 500, 572, 108, T.sunken, { rx: 10, stroke: T.stroke }),
		rect(636, 522, 120, 24, T.brandSoft, { rx: 12 }),
		rect(768, 522, 140, 24, T.lineSoft, { rx: 12 }),
		rect(920, 522, 160, 24, T.lineSoft, { rx: 12 }),
		rect(636, 566, 400, 12, T.dot, { rx: 6 }),
		"  <!-- действия -->",
		rect(612, 632, 120, 44, T.lineSoft, { rx: 10 }),
		rect(744, 632, 120, 44, T.lineSoft, { rx: 10 }),
		rect(1064, 632, 120, 44, T.brand, { rx: 10 }),
		rect(1096, 650, 56, 12, T.onBrand, { rx: 6 }),
	);
}

// ---------------------------------------------------------------------------
// Шаг 5 — отправленные отклики в очереди
// ---------------------------------------------------------------------------
function sentRow(T, y) {
	return [
		rect(256, y, 960, 92, T.panel, { rx: 16, stroke: T.stroke }),
		rect(288, y + 24, 280, 14, T.dot, { rx: 7 }),
		rect(288, y + 54, 180, 10, T.dot, { rx: 5 }),
		rect(1060, y + 34, 124, 24, T.ok, { rx: 12 }),
		`  <path d="M1078 ${y + 46} l6 6 l12 -12" stroke="${T.brand}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
	].join("\n");
}

function stepApply(T) {
	return svg(
		"Отправленные отклики в очереди Otklik",
		titleBar(T),
		sidebar(T, 0),
		rect(256, 76, 180, 16, T.dot, { rx: 8 }),
		rect(1000, 72, 216, 40, T.ok, { rx: 10 }),
		rect(1040, 86, 136, 12, T.dot, { rx: 6 }),
		sentRow(T, 168),
		sentRow(T, 276),
		sentRow(T, 384),
		sentRow(T, 492),
		sentRow(T, 600),
	);
}

// ---------------------------------------------------------------------------
// Hero (app-light.svg / app-dark.svg) — общий вид приложения
// ---------------------------------------------------------------------------
function heroSidebar(T) {
	return [
		rect(0, 44, 232, 721, T.panel),
		rect(24, 76, 88, 16, T.line, { rx: 8 }),
		rect(16, 120, 200, 40, T.brandSoft, { rx: 10 }),
		rect(32, 134, 18, 12, T.brand, { rx: 4 }),
		rect(62, 133, 104, 14, T.line, { rx: 7 }),
		rect(32, 186, 18, 12, T.dot, { rx: 4 }),
		rect(62, 185, 84, 14, T.dot, { rx: 7 }),
		rect(32, 234, 18, 12, T.dot, { rx: 4 }),
		rect(62, 233, 120, 14, T.dot, { rx: 7 }),
		rect(32, 282, 18, 12, T.dot, { rx: 4 }),
		rect(62, 281, 68, 14, T.dot, { rx: 7 }),
		rect(16, 693, 200, 48, T.lineSoft, { rx: 10 }),
		circle(44, 717, 14, T.dot),
		rect(68, 711, 88, 12, T.dot, { rx: 6 }),
	].join("\n");
}

function heroQueueCard(T, y, pillFill) {
	return [
		rect(256, y, 344, 96, T.panel, { rx: 12, stroke: T.stroke }),
		rect(256, y, 4, 96, T.brand, { rx: 2 }),
		rect(280, y + 22, 188, 14, T.dot, { rx: 7 }),
		rect(280, y + 50, 120, 12, T.dot, { rx: 6 }),
		rect(524, y + 18, 52, 20, pillFill, { rx: 10 }),
	].join("\n");
}

function hero(T) {
	return svg(
		"Интерфейс Otklik",
		titleBar(T),
		heroSidebar(T),
		"  <!-- очередь вакансий -->",
		rect(256, 76, 140, 16, T.line, { rx: 8 }),
		heroQueueCard(T, 112, T.ok),
		heroQueueCard(T, 224, T.lineSoft),
		heroQueueCard(T, 336, T.lineSoft),
		heroQueueCard(T, 448, T.lineSoft),
		heroQueueCard(T, 560, T.lineSoft),
		"  <!-- письмо -->",
		rect(632, 112, 584, 592, T.panel, { rx: 16, stroke: T.stroke }),
		rect(664, 144, 180, 16, T.line, { rx: 8 }),
		rect(664, 176, 120, 12, T.dot, { rx: 6 }),
		rect(664, 216, 520, 336, T.sunken, { rx: 12, stroke: T.stroke }),
		rect(688, 244, 472, 12, T.dot, { rx: 6 }),
		rect(688, 272, 440, 12, T.dot, { rx: 6 }),
		rect(688, 300, 472, 12, T.dot, { rx: 6 }),
		rect(688, 328, 392, 12, T.dot, { rx: 6 }),
		rect(688, 368, 472, 12, T.dot, { rx: 6 }),
		rect(688, 396, 456, 12, T.dot, { rx: 6 }),
		rect(688, 424, 336, 12, T.dot, { rx: 6 }),
		rect(688, 464, 472, 12, T.dot, { rx: 6 }),
		rect(688, 492, 248, 12, T.dot, { rx: 6 }),
		rect(664, 588, 120, 40, T.lineSoft, { rx: 10 }),
		rect(796, 588, 120, 40, T.lineSoft, { rx: 10 }),
		rect(1064, 588, 120, 40, T.brand, { rx: 10 }),
		rect(1096, 602, 56, 12, T.onBrand, { rx: 6 }),
	);
}

// ---------------------------------------------------------------------------

mkdirSync(SCREENS_DIR, { recursive: true });

const STEP_SCREENS = {
	"step-1-auth": stepAuth,
	"step-2-settings": stepSettings,
	"step-3-search": stepSearch,
	"step-4-review": stepReview,
	"step-5-apply": stepApply,
};

let written = 0;

for (const [name, build] of Object.entries(STEP_SCREENS)) {
	writeFileSync(join(SCREENS_DIR, `${name}.light.svg`), build(LIGHT));
	writeFileSync(join(SCREENS_DIR, `${name}.dark.svg`), build(DARK));
	written += 2;
}

writeFileSync(join(PUBLIC_DIR, "app-light.svg"), hero(LIGHT));
writeFileSync(join(PUBLIC_DIR, "app-dark.svg"), hero(DARK));
written += 2;

console.log(`Готово: ${written} файлов записано в ${PUBLIC_DIR}.`);
