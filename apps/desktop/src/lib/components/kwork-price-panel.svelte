<script lang="ts">
import { m } from "$lib/paraglide/messages";
import CircleDollarSign from "@lucide/svelte/icons/circle-dollar-sign";

const {
	percent,
	pending,
	onSave,
}: {
	percent: number;
	pending: boolean;
	onSave: (percent: number) => void;
} = $props();

let value = $state(percent);
let lastProp = $state(percent);

$effect(() => {
	if (percent !== lastProp) {
		value = percent;
		lastProp = percent;
	}
});

function commit(event: Event) {
	const next = Number((event.currentTarget as HTMLInputElement).value);
	value = next;
	if (next !== percent) {
		onSave(next);
	}
}
</script>

<section class="bg-card space-y-3 rounded-lg border px-4 py-3 text-sm">
	<div class="flex items-center gap-2.5">
		<CircleDollarSign class="text-muted-foreground size-4 shrink-0" />
		<span class="font-medium">{m.queue_kwork_price_title()}</span>
		<span class="text-muted-foreground ml-auto font-mono tabular-nums">
			{value}%
		</span>
	</div>

	<input
		type="range"
		min="0"
		max="100"
		step="5"
		bind:value
		onchange={commit}
		disabled={pending}
		aria-label={m.queue_kwork_price_title()}
		class="accent-primary h-1.5 w-full cursor-pointer appearance-none rounded-full bg-muted disabled:cursor-not-allowed disabled:opacity-50"
	/>

	<div class="text-muted-foreground flex items-center justify-between text-xs">
		<span>{m.queue_kwork_price_desired()}</span>
		<span>{m.queue_kwork_price_max()}</span>
	</div>

	<p class="text-muted-foreground text-xs">{m.queue_kwork_price_hint()}</p>
</section>
