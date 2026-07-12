<script lang="ts">
import type { Icon as IconType } from "@lucide/svelte";

const {
	href,
	label,
	icon: Icon,
	active,
	count = null,
}: {
	href: string;
	label: string;
	icon: typeof IconType;
	active: boolean;
	count?: number | null;
} = $props();

// Счётчик показывается ТОЛЬКО когда есть что показать. `null` — данные ещё не
// пришли; `0` — работы нет. В обоих случаях плашка не рисуется: постоянный ноль
// это шум, который перестают замечать.
const showCount = $derived(count !== null && count > 0);
</script>

<a
	{href}
	aria-current={active ? "page" : undefined}
	class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors {active
		? 'font-medium text-foreground'
		: 'text-muted-foreground hover:bg-accent hover:text-foreground'}"
>
	<Icon class="size-[18px] shrink-0" />
	<span class="min-w-0 flex-1 truncate">{label}</span>
	{#if showCount}
		<!--
			Единственный акцент палитры потрачен на единственный сигнал, зовущий
			к действию. tabular-nums — чтобы плашка не дёргалась при 9 → 10.
		-->
		<span
			data-testid="nav-row-count"
			class="inline-flex min-w-5 shrink-0 items-center justify-center rounded-full bg-primary px-1.5 py-0.5 font-mono text-[11px] leading-none font-medium text-primary-foreground tabular-nums"
		>
			{count}
		</span>
	{/if}
</a>
