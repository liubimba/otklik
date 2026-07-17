<script lang="ts">
import type { LucideIcon } from "@lucide/svelte";
import type { Snippet } from "svelte";

interface Props {
	icon?: LucideIcon;
	title: string;
	description?: string;
	children?: Snippet;
}

const { icon: Icon, title, description, children }: Props = $props();
</script>

<div
        class="text-muted-foreground flex flex-col items-center gap-3 rounded-lg border border-dashed p-10 text-center"
>
    {#if Icon}
        <Icon class="size-8 opacity-60"/>
    {/if}
    <div class="space-y-1">
        <p class="text-foreground text-sm font-medium">{title}</p>
        {#if description}
            <p class="text-sm">{description}</p>
        {/if}
    </div>
    {@render children?.()}
</div>
