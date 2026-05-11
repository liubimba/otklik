<script lang="ts">
import { cn } from "$lib/utils.js";
import type { Dialog as DialogPrimitive } from "bits-ui";

const {
	ref = $bindable(null),
	class: className,
	...restProps
}: DialogPrimitive.TitleProps = $props();
</script>

<DialogPrimitive.Title
	bind:ref
	data-slot="dialog-title"
	class={cn("text-sm font-medium", className)}
	{...restProps}
/>
