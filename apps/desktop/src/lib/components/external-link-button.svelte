<script lang="ts">
import { openExternal } from "$lib/open-external";
import type { Snippet } from "svelte";

const {
	href,
	class: className = "",
	ariaLabel,
	children,
}: {
	href: string;
	class?: string;
	ariaLabel?: string;
	children: Snippet;
} = $props();

function onclick(event: MouseEvent): void {
	event.stopPropagation();
	void openExternal(href);
}
</script>

<button type="button" {onclick} class={className} aria-label={ariaLabel}>
	{@render children()}
</button>
