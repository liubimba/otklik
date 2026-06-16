<script lang="ts">
import type { Vacancy } from "$lib/api/types";
import * as m from "$lib/paraglide/messages";
import { ExternalLink } from "@lucide/svelte";

interface Props {
	vacancy: Vacancy;
	onclick?: (vacancy: Vacancy) => void;
}

const { vacancy, onclick }: Props = $props();

function handleClick() {
	onclick?.(vacancy);
}

function handleKeydown(e: KeyboardEvent) {
	if (e.key === "Enter" || e.key === " ") {
		e.preventDefault();
		onclick?.(vacancy);
	}
}
</script>

<div
	role="button"
	tabindex="0"
	onclick={handleClick}
	onkeydown={handleKeydown}
	class="bg-card text-card-foreground hover:bg-muted/40 focus-visible:ring-ring/40 flex cursor-pointer items-start gap-4 rounded-lg border p-4 transition-colors focus-visible:outline-none focus-visible:ring-2"
>
	<div class="min-w-0 flex-1 space-y-1">
		<h3 class="truncate text-base font-medium">{vacancy.title}</h3>
		{#if vacancy.company_name}
			<p class="text-muted-foreground truncate text-sm">
				{vacancy.company_name}
			</p>
		{/if}
		{#if vacancy.salary}
			<p class="text-sm">{vacancy.salary}</p>
		{/if}
		{#if vacancy.work_location}
			<p class="text-muted-foreground text-sm">{vacancy.work_location}</p>
		{/if}
	</div>
	<a
		href={vacancy.apply_link}
		target="_blank"
		rel="noopener noreferrer"
		onclick={(e) => e.stopPropagation()}
		aria-label={m.queue_card_open_external()}
		class="text-muted-foreground hover:text-foreground focus-visible:ring-ring/40 -m-1 rounded p-1 focus-visible:outline-none focus-visible:ring-2"
	>
		<ExternalLink class="size-4" />
	</a>
</div>
