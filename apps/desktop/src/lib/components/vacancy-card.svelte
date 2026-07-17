<script lang="ts">
import type { ProcessingState, Vacancy } from "$lib/api/types";
import { Badge } from "$lib/components/ui/badge";
import * as m from "$lib/paraglide/messages";
import { createApplicationQuery } from "$lib/queries/applications";
import ExternalLink from "@lucide/svelte/icons/external-link";

interface Props {
	vacancy: Vacancy;
	status?: ProcessingState | null;
	onclick?: (vacancy: Vacancy) => void;
}

const { vacancy, status: statusProp, onclick }: Props = $props();

const application = createApplicationQuery(() =>
	statusProp !== undefined ? null : vacancy.id,
);

const effectiveStatus = $derived(
	statusProp !== undefined ? statusProp : application.data?.status,
);

type StatusBadge = {
	label: string;
	variant: "default" | "success" | "secondary" | "destructive" | "ghost";
};

const statusBadge = $derived.by((): StatusBadge | null => {
	switch (effectiveStatus) {
		case "letter_pending":
			return { label: m.card_status_letter_pending(), variant: "secondary" };
		case "letter_ready":
			return { label: m.card_status_letter_ready(), variant: "default" };
		case "letter_reviewing":
			return { label: m.card_status_letter_reviewing(), variant: "secondary" };
		case "letter_sending":
			return { label: m.card_status_letter_sending(), variant: "secondary" };
		case "letter_sent":
			return { label: m.card_status_letter_sent(), variant: "success" };
		case "error":
			return { label: m.card_status_error(), variant: "destructive" };
		case "skipped":
			return { label: m.card_status_skipped(), variant: "ghost" };
		default:
			return null;
	}
});

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
	class="bg-surface-2 text-card-foreground shadow-e1 hover:shadow-e2 hover:bg-muted/40 focus-visible:ring-ring/40 flex cursor-pointer items-start gap-4 rounded-lg border p-4 transition-[background-color,box-shadow] duration-200 focus-visible:outline-none focus-visible:ring-2 [contain:layout_paint]"
>
	<div class="min-w-0 flex-1 space-y-1">
		<h3 class="truncate text-base font-medium">{vacancy.title}</h3>
		{#if vacancy.company_name}
			<p class="text-muted-foreground truncate text-sm">
				{vacancy.company_name}
			</p>
		{/if}
		{#if vacancy.salary}
			<p class="font-mono text-sm">{vacancy.salary}</p>
		{/if}
		{#if vacancy.work_location}
			<p class="text-muted-foreground text-sm">{vacancy.work_location}</p>
		{/if}
	</div>
	<div
		class="flex shrink-0 flex-col items-end justify-between gap-2 self-stretch"
	>
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
		{#if statusBadge}
			<Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
		{/if}
	</div>
</div>
