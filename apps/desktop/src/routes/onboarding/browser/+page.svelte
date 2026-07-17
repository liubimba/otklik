<script lang="ts">
import { goto } from "$app/navigation";
import LiveStatus from "$lib/components/live-status.svelte";
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
import CircleAlert from "@lucide/svelte/icons/circle-alert";
import CircleCheck from "@lucide/svelte/icons/circle-check";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
import { onMount } from "svelte";
import { BrowserFlow } from "./browser-flow.svelte";

const flow = new BrowserFlow();
const percent = $derived(Math.round(flow.percent));

const liveStatus = $derived.by(() => {
	switch (flow.screen) {
		case "checking":
			return m.browser_setup_checking();
		case "downloading":
			return m.browser_setup_progress({ percent });
		case "ready":
			return m.browser_setup_ready();
		case "error":
			return m.browser_setup_error_title();
	}
});

onMount(() => {
	void flow.start();
});

$effect(() => {
	if (flow.screen === "ready") {
		void goto("/onboarding/model");
	}
});
</script>

<div class="container mx-auto flex min-h-full max-w-xl flex-col justify-center gap-6 p-6">
    <header class="flex items-center justify-between gap-3">
        <p class="text-muted-foreground font-mono text-xs uppercase tracking-wide">
            {m.browser_setup_header()}
        </p>
    </header>

    <LiveStatus text={liveStatus}/>

    <section class="bg-card space-y-4 rounded-lg border p-6 shadow-[var(--elevation-1)]">
        {#if flow.screen === "checking"}
            <div class="flex items-start gap-3">
                <LoaderCircle
                        class="text-muted-foreground size-5 shrink-0 motion-safe:animate-spin"
                />
                <div class="space-y-1">
                    <h1 class="text-lg font-semibold">{m.browser_setup_title()}</h1>
                    <p class="text-muted-foreground text-sm">
                        {m.browser_setup_checking()}
                    </p>
                </div>
            </div>

        {:else if flow.screen === "downloading"}
            <div class="space-y-2">
                <h1 class="text-lg font-semibold">{m.browser_setup_title()}</h1>
                <p class="text-muted-foreground text-sm">
                    {m.browser_setup_subtitle()}
                </p>
                <p class="text-muted-foreground font-mono text-sm">
                    {m.browser_setup_progress({ percent })}
                </p>
            </div>
            <div
                    role="progressbar"
                    aria-label={m.browser_setup_progress_label()}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percent}
                    class="bg-muted h-2 w-full overflow-hidden rounded-full"
            >
                <div
                        class="bg-primary h-full rounded-full motion-safe:transition-[width] motion-safe:duration-300"
                        style="width: {percent}%"
                ></div>
            </div>

        {:else if flow.screen === "ready"}
            <div class="flex items-start gap-3">
                <CircleCheck class="text-primary size-5 shrink-0"/>
                <h1 class="text-lg font-semibold">{m.browser_setup_ready()}</h1>
            </div>

        {:else if flow.screen === "error"}
            <div class="flex items-start gap-3">
                <CircleAlert class="text-destructive size-5 shrink-0"/>
                <div class="space-y-1">
                    <h1 class="text-lg font-semibold">
                        {m.browser_setup_error_title()}
                    </h1>
                    <p class="text-muted-foreground break-words text-sm">{flow.error}</p>
                </div>
            </div>
            <Button class="w-full cursor-pointer" onclick={() => flow.retry()}>
                {m.setup_retry()}
            </Button>
        {/if}
    </section>
</div>
