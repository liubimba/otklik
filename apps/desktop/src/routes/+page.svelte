<script lang="ts">
import AppMark from "$lib/components/app-mark.svelte";
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
</script>

<!--
	Landing. The animated dotted canvas now lives in the layout and backs every
	screen, so this section stays transparent and lets it show through.
	Not a <main>: +layout.svelte already renders one around {@render children()}.
-->
<section
	class="flex min-h-full flex-col items-center justify-center gap-6 p-6 text-center"
>
	<div class="flex flex-col items-center gap-6">
		<span
			class="bg-primary text-primary-foreground flex size-16 items-center justify-center rounded-2xl shadow-e2"
		>
			<AppMark class="size-9" />
		</span>

		<div class="space-y-2">
			<h1 class="font-mono text-3xl font-semibold">{m.nav_app_title()}</h1>
			<p class="text-muted-foreground max-w-md text-sm">{m.home_tagline()}</p>
		</div>

		<div class="flex flex-wrap items-center justify-center gap-3">
			<Button href="/queue">{m.home_open_queue()}</Button>
			<Button href="/settings" variant="outline">{m.home_open_settings()}</Button>
		</div>
	</div>
</section>
