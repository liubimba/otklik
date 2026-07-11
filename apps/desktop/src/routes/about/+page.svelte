<script lang="ts">
import AppMark from "$lib/components/app-mark.svelte";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
import { updater } from "$lib/stores/updater.svelte";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
import RefreshCw from "@lucide/svelte/icons/refresh-cw";
import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
import { getVersion } from "@tauri-apps/api/app";
import { onMount } from "svelte";
import { toast } from "svelte-sonner";

// The running app's version comes from tauri.conf.json via getVersion(). It's
// only resolvable inside the Tauri runtime, so it's read once on mount and left
// blank if unavailable (e.g. a plain browser preview).
let version = $state("");
onMount(async () => {
	try {
		version = await getVersion();
	} catch {
		version = "";
	}
});

const steps = [
	m.about_usage_step_1(),
	m.about_usage_step_2(),
	m.about_usage_step_3(),
	m.about_usage_step_4(),
	m.about_usage_step_5(),
];

async function checkUpdates() {
	const found = await updater.check();
	if (found) return; // the update dialog shows itself
	if (updater.error) {
		toast.error(m.update_check_failed({ error: updater.error }));
	} else {
		toast.success(m.update_up_to_date());
	}
}
</script>

<div class="container mx-auto max-w-2xl space-y-6 p-6">
	<div class="flex items-center gap-4">
		<span
			class="bg-primary text-primary-foreground flex size-14 shrink-0 items-center justify-center rounded-2xl shadow-e2"
		>
			<AppMark class="size-8" />
		</span>
		<div class="space-y-1.5">
			<h1 class="font-mono text-2xl font-semibold">{m.nav_app_title()}</h1>
			{#if version}
				<Badge variant="secondary" class="font-mono"
					>{m.about_version_label()} {version}</Badge
				>
			{/if}
		</div>
	</div>

	<section class="bg-surface-2 space-y-2 rounded-lg border p-5 shadow-e1">
		<h2 class="text-lg font-medium">{m.about_description_title()}</h2>
		<p class="text-muted-foreground text-sm">{m.about_description()}</p>
	</section>

	<section class="bg-surface-2 space-y-3 rounded-lg border p-5 shadow-e1">
		<h2 class="text-lg font-medium">{m.about_usage_title()}</h2>
		<ol class="space-y-2.5 text-sm">
			{#each steps as step, i (i)}
				<li class="flex gap-3">
					<span
						class="bg-primary/10 text-primary flex size-6 shrink-0 items-center justify-center rounded-full font-mono text-xs font-semibold"
						>{i + 1}</span
					>
					<span class="text-muted-foreground pt-0.5">{step}</span>
				</li>
			{/each}
		</ol>
	</section>

	<!-- Warning box, reusing the onboarding disclaimer strings. -->
	<section
		class="border-destructive/30 bg-destructive/10 space-y-2 rounded-lg border p-5"
	>
		<h2 class="text-destructive flex items-center gap-2 text-lg font-medium">
			<TriangleAlert class="size-4" />
			{m.about_disclaimer_title()}
		</h2>
		<p class="text-foreground/80 text-sm">
			{m.onboarding_risk_intro()}
			<strong>{m.onboarding_risk_tos()}</strong>{m.onboarding_risk_ban()}
		</p>
		<p class="text-foreground/80 text-sm">
			{m.onboarding_own_risk_intro()}
			<strong>{m.onboarding_own_risk_strong()}</strong>{m.onboarding_own_risk_rest()}
		</p>
	</section>

	<section class="bg-surface-2 space-y-3 rounded-lg border p-5 shadow-e1">
		<div class="space-y-1">
			<h2 class="text-lg font-medium">{m.about_updates_title()}</h2>
			<p class="text-muted-foreground text-sm">{m.about_updates_hint()}</p>
		</div>
		<div class="flex items-center gap-3">
			<Button
				variant="outline"
				onclick={checkUpdates}
				disabled={updater.checking}
			>
				{#if updater.checking}
					<LoaderCircle class="animate-spin" />
					{m.about_checking()}
				{:else}
					<RefreshCw />
					{m.about_check_updates()}
				{/if}
			</Button>
			{#if version}
				<span class="text-muted-foreground font-mono text-xs"
					>{m.about_version_label()} {version}</span
				>
			{/if}
		</div>
	</section>
</div>
