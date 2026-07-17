<script lang="ts">
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
import CircleAlert from "@lucide/svelte/icons/circle-alert";

interface Props {
	message: string;
	onRetry?: () => void;
}

const { message, onRetry }: Props = $props();
</script>

<div
        class="border-destructive/30 bg-destructive/5 flex flex-col items-center gap-3 rounded-lg border p-6 text-center"
>
    <CircleAlert class="text-destructive size-6"/>
    <p class="text-destructive text-sm">{message}</p>
    {#if onRetry}
        <Button variant="outline" size="sm" onclick={onRetry}>
            {m.action_retry()}
        </Button>
    {/if}
</div>
