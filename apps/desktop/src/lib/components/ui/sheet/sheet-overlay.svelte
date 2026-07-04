<script lang="ts">
	import { Dialog as SheetPrimitive } from "bits-ui";
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		...restProps
	}: SheetPrimitive.OverlayProps = $props();
</script>

<!--
	Deliberately no `backdrop-blur-*` — WebKitGTK re-composites every
	pixel under the overlay per frame, which cost 220 ms paint per
	frame on Tauri Linux with the queue list in the background (see
	PERF_BASELINE.md → regenerate scenario). `bg-black/10` alone reads
	as a soft dim, which is enough signal for "modal is open" in a
	desktop shell.
-->
<SheetPrimitive.Overlay
	bind:ref
	data-slot="sheet-overlay"
	class={cn("bg-black/10 text-xs/relaxed fixed inset-0 z-50", className)}
	{...restProps}
/>
