<script lang="ts">
import * as m from "$lib/paraglide/messages";
import { connection } from "$lib/stores/connection.svelte";
import WifiOff from "@lucide/svelte/icons/wifi-off";

const offline = $derived(connection.isOffline);
</script>

{#if offline}
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
