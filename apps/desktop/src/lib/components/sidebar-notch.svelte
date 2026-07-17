<script lang="ts">
type Notch = { top: number; h: number; left: number };

const {
	width,
	height,
	notch,
}: { width: number; height: number; notch: Notch | null } = $props();

const CR = 18;
const NR = 14;
const PAD = 4;

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
	style="filter: drop-shadow(0 8px 18px var(--elevation-2-shadow-2)) drop-shadow(0 2px 5px var(--elevation-2-shadow-1));"
	aria-hidden="true"
>
	<path
		{d}
		class="fill-sidebar stroke-1 stroke-border [transition:d_220ms_cubic-bezier(0.4,0,0.2,1)] motion-reduce:transition-none"
	/>
</svg>
