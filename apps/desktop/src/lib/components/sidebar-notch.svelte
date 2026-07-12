<script lang="ts">
/**
 * Фон сайдбара — не div, а SVG-путь. В правом крае выгрызена ниша за активной
 * строкой: карточка там отсутствует, и сквозь неё виден точечный холст. Контент
 * лежит на том же холсте, поэтому активная строка визуально сливается с ним.
 *
 * Компонент НИЧЕГО не измеряет — геометрию считает владелец и передаёт пропсами.
 * Так вся математика остаётся в одном месте, а этот файл занят только формой.
 */
type Notch = { top: number; h: number; left: number };

const {
	width,
	height,
	notch,
}: { width: number; height: number; notch: Notch | null } = $props();

const CR = 18; // внешнее скругление карточки
const NR = 14; // скругление ниши
const PAD = 4; // зазор холста вокруг активной строки

function roundedRect(w: number, h: number): string {
	return `M ${CR},0 L ${w - CR},0 Q ${w},0 ${w},${CR} L ${w},${h - CR} Q ${w},${h} ${w - CR},${h} L ${CR},${h} Q 0,${h} 0,${h - CR} L 0,${CR} Q 0,0 ${CR},0 Z`;
}

const d = $derived.by(() => {
	const w = width;
	const h = height;
	if (h < CR * 2) return "";
	if (!notch) return roundedRect(w, h);

	const nt = Math.max(CR + NR, notch.top - PAD);
	const nb = Math.min(h - CR - NR, notch.top + notch.h + PAD);
	const nl = Math.max(CR, notch.left - PAD);
	// Ниша ниже двух своих скруглений вырождается в кашу — рисуем прямоугольник.
	if (nb - nt < NR * 2 + 2) return roundedRect(w, h);

	return [
		`M ${CR},0`,
		`L ${w - CR},0`,
		`Q ${w},0 ${w},${CR}`,
		`L ${w},${nt - NR}`,
		`Q ${w},${nt} ${w - NR},${nt}`,
		`L ${nl + NR},${nt}`,
		`Q ${nl},${nt} ${nl},${nt + NR}`,
		`L ${nl},${nb - NR}`,
		`Q ${nl},${nb} ${nl + NR},${nb}`,
		`L ${w - NR},${nb}`,
		`Q ${w},${nb} ${w},${nb + NR}`,
		`L ${w},${h - CR}`,
		`Q ${w},${h} ${w - CR},${h}`,
		`L ${CR},${h}`,
		`Q 0,${h} 0,${h - CR}`,
		`L 0,${CR}`,
		`Q 0,0 ${CR},0`,
		"Z",
	].join(" ");
});
</script>

<svg
	class="pointer-events-none absolute inset-0 size-full overflow-visible"
	viewBox="0 0 {width} {height}"
	preserveAspectRatio="none"
	style="filter: drop-shadow(0 8px 18px rgb(0 0 0 / 0.13)) drop-shadow(0 2px 5px rgb(0 0 0 / 0.08));"
	aria-hidden="true"
>
	<!--
		Единственный момент движения во всём приложении: при смене раздела ниша
		едет к новой строке. Под prefers-reduced-motion она перескакивает.
	-->
	<path
		{d}
		class="fill-sidebar stroke-1 stroke-border [transition:d_220ms_cubic-bezier(0.4,0,0.2,1)] motion-reduce:transition-none"
	/>
</svg>
