<script lang="ts">
import * as m from "$lib/paraglide/messages";
import { connection } from "$lib/stores/connection.svelte";
import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
import WifiOff from "@lucide/svelte/icons/wifi-off";

const offline = $derived(connection.isOffline);
const failed = $derived(connection.isFailed);
const detail = $derived(connection.detail);
</script>

{#if failed}
	<div
		role="alert"
		aria-live="assertive"
		class="flex shrink-0 flex-col gap-0.5 border-b border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs text-destructive"
	>
		<div class="flex items-center gap-2">
			<TriangleAlert class="size-3.5 shrink-0" />
			<span>{m.connection_failed()}</span>
		</div>
		{#if detail}
			<span class="truncate pl-5.5 font-mono text-destructive/70">{detail}</span>
		{/if}
	</div>
{:else if offline}
	<div
		role="status"
		aria-live="polite"
		class="flex shrink-0 items-center justify-center gap-2 border-b bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground"
	>
		<WifiOff class="size-3.5 shrink-0" />
		<span>{m.connection_offline()}</span>
		<span
			class="size-1.5 shrink-0 rounded-full bg-muted-foreground/60 motion-safe:animate-pulse"
			aria-hidden="true"
		></span>
	</div>
{/if}
