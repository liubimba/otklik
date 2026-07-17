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

const showCount = $derived(count !== null && count > 0);
</script>

<a
	{href}
	aria-current={active ? "page" : undefined}
	class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-[margin,background-color,color] duration-200 motion-reduce:transition-none {active
		? 'ml-4 font-medium text-foreground'
		: 'text-muted-foreground hover:bg-accent hover:text-foreground'}"
>
	<Icon class="size-[18px] shrink-0" />
	<span class="min-w-0 flex-1 truncate">{label}</span>
	{#if showCount}
		<span
			data-testid="nav-row-count"
			class="inline-flex min-w-5 shrink-0 items-center justify-center rounded-full bg-primary px-1.5 py-0.5 font-mono text-[11px] leading-none font-medium text-primary-foreground tabular-nums"
		>
			{count}
		</span>
	{/if}
</a>
