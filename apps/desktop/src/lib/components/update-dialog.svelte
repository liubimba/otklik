<script lang="ts">
import { Button } from "$lib/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "$lib/components/ui/dialog";
import * as m from "$lib/paraglide/messages";
import { updater } from "$lib/stores/updater.svelte";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";

const open = $derived(updater.available !== null);
</script>

<Dialog
	{open}
	onOpenChange={(next) => {
		if (!next) updater.dismiss();
	}}
>
	<DialogContent>
		<DialogHeader>
			<DialogTitle>
				{m.update_available_title({
					version: updater.available?.version ?? "",
				})}
			</DialogTitle>
			<DialogDescription>{m.update_available_hint()}</DialogDescription>
		</DialogHeader>

		{#if updater.available?.body}
			<div
				class="bg-surface-2 text-muted-foreground max-h-40 overflow-y-auto rounded-md border p-3 text-sm whitespace-pre-wrap"
			>
				{updater.available.body}
			</div>
		{/if}

		{#if updater.error}
			<p
				role="alert"
				class="border-destructive/30 bg-destructive/10 text-destructive rounded-md border p-3 text-sm"
			>
				{m.update_failed({ error: updater.error })}
			</p>
		{/if}

		<DialogFooter>
			<Button
				variant="outline"
				onclick={() => updater.dismiss()}
				disabled={updater.installing}
			>
				{m.update_later()}
			</Button>
			<Button onclick={() => updater.install()} disabled={updater.installing}>
				{#if updater.installing}
					<LoaderCircle class="animate-spin" />
					{m.update_installing()}
				{:else}
					{m.update_install()}
				{/if}
			</Button>
		</DialogFooter>
	</DialogContent>
</Dialog>
