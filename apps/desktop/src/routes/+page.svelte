<script lang="ts">
import AppMark from "$lib/components/app-mark.svelte";
import DottedBackground from "$lib/components/dotted-background.svelte";
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
import { mode } from "mode-watcher";

// The canvas reads `--border` off the document, so it has to be told when the
// theme flips. `dark` is a change signal, not a colour.
const dark = $derived(mode.current === "dark");
</script>

<!--
	The only screen that carries the animated canvas: no lists, no scrolling, so
	the per-frame repaint costs nothing that matters. It gates itself on
	prefers-reduced-motion. Everything else gets the static `bg-dotted` grid from
	the layout, which this section covers with its own opaque background.
-->
<!-- Not a <main>: Sidebar.Inset already renders one (see description/vault/UI.md). -->
<section
        class="bg-background relative flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-6 overflow-hidden p-6 text-center"
>
    <DottedBackground {dark}/>

    <div class="relative flex flex-col items-center gap-6">
        <span
                class="bg-primary text-primary-foreground flex size-16 items-center justify-center rounded-2xl shadow-e2"
        >
            <AppMark class="size-9"/>
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
