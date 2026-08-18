<script lang="ts">
import { createActions } from "$lib/actions";
import type {
	ContextSource,
	ContextSourceStatus,
	ContextSourceWrite,
} from "$lib/api/types";
import ErrorState from "$lib/components/error-state.svelte";
import ExternalLinkButton from "$lib/components/external-link-button.svelte";
import { Badge, type BadgeVariant } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import { Input } from "$lib/components/ui/input";
import { Label } from "$lib/components/ui/label";
import { Skeleton } from "$lib/components/ui/skeleton";
import { m } from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import ExternalLink from "@lucide/svelte/icons/external-link";
import Plus from "@lucide/svelte/icons/plus";
import RefreshCw from "@lucide/svelte/icons/refresh-cw";
import Trash2 from "@lucide/svelte/icons/trash-2";
import { useQueryClient } from "@tanstack/svelte-query";

const queryClient = useQueryClient();
const actions = createActions(queryClient).sources;

const sources = query.sources.create();

let label = $state("");
let url = $state("");
let description = $state("");

const statusVariant: Record<ContextSourceStatus, BadgeVariant> = {
	ok: "success",
	error: "destructive",
	pending: "secondary",
};

const statusLabel: Record<ContextSourceStatus, () => string> = {
	ok: m.settings_ai_sources_status_ok,
	error: m.settings_ai_sources_status_error,
	pending: m.settings_ai_sources_status_pending,
};

function kindLabel(kind: ContextSource["kind"]): string {
	return kind === "github" ? "GitHub" : "Web";
}

function formattedFetchedAt(source: ContextSource): string {
	if (!source.fetched_at) return m.settings_ai_sources_fetched_never();
	return new Date(source.fetched_at).toLocaleString();
}

function submitAdd(event: SubmitEvent) {
	event.preventDefault();
	const trimmedLabel = label.trim();
	const trimmedUrl = url.trim();
	if (!trimmedLabel || !trimmedUrl) return;
	const body: ContextSourceWrite = {
		label: trimmedLabel,
		url: trimmedUrl,
		description: description.trim() || null,
	};
	actions.add.mutate(body, {
		onSuccess: () => {
			label = "";
			url = "";
			description = "";
		},
	});
}
</script>

<div class="space-y-3">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="space-y-1">
			<p class="text-sm font-medium">{m.settings_ai_sources_label()}</p>
			<p class="text-muted-foreground text-sm">
				{m.settings_ai_sources_hint()}
			</p>
		</div>
		<Button
			type="button"
			variant="outline"
			size="sm"
			class="shrink-0"
			onclick={() => actions.refreshAll.mutate()}
			disabled={actions.refreshAll.isPending ||
				(sources.data?.length ?? 0) === 0}
		>
			<RefreshCw class="size-4" />
			{m.settings_ai_sources_refresh_all()}
		</Button>
	</div>

	{#if sources.isPending}
		<div class="space-y-2">
			{#each [0, 1] as row (row)}
				<Skeleton class="h-16 w-full rounded-md" />
			{/each}
		</div>
	{:else if sources.isError}
		<ErrorState
			message={m.settings_ai_sources_load_error({
				error: sources.error?.message ?? "unknown",
			})}
			onRetry={() => sources.refetch()}
		/>
	{:else if (sources.data?.length ?? 0) === 0}
		<p
			class="text-muted-foreground rounded-md border border-dashed p-6 text-center text-sm"
		>
			{m.settings_ai_sources_empty()}
		</p>
	{:else}
		<div class="space-y-2">
			{#each sources.data ?? [] as source (source.id)}
				<div class="space-y-2 rounded-md border p-3">
					<div class="flex items-start justify-between gap-2">
						<div class="min-w-0 space-y-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class="truncate font-medium">{source.label}</span>
								<Badge variant="outline">{kindLabel(source.kind)}</Badge>
								<Badge variant={statusVariant[source.status]}>
									{statusLabel[source.status]()}
								</Badge>
							</div>
							<div
								class="text-muted-foreground flex flex-wrap items-center gap-2 text-xs"
							>
								<ExternalLinkButton
									href={source.url}
									class="hover:text-foreground inline-flex min-w-0 items-center gap-1"
								>
									<span class="max-w-64 truncate">{source.url}</span>
									<ExternalLink class="size-3 shrink-0" />
								</ExternalLinkButton>
								<span>&middot;</span>
								<span>{formattedFetchedAt(source)}</span>
							</div>
							{#if source.status === "error" && source.error}
								<p class="text-destructive text-xs">{source.error}</p>
							{/if}
						</div>
						<div class="flex shrink-0 gap-1">
							<Button
								type="button"
								variant="ghost"
								size="icon-sm"
								onclick={() => actions.refresh.mutate(source.id)}
								disabled={actions.refresh.isPending}
								aria-label={m.settings_ai_sources_refresh()}
							>
								<RefreshCw class="size-4" />
							</Button>
							<Button
								type="button"
								variant="ghost"
								size="icon-sm"
								onclick={() => actions.remove.mutate(source.id)}
								disabled={actions.remove.isPending}
								aria-label={m.settings_ai_sources_delete()}
							>
								<Trash2 class="size-4" />
							</Button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<form onsubmit={submitAdd} class="space-y-3 rounded-md border p-3">
		<div class="grid gap-3 sm:grid-cols-2">
			<div class="space-y-1.5">
				<Label for="context-source-label">
					{m.settings_ai_sources_label_field()}
				</Label>
				<Input id="context-source-label" bind:value={label} />
			</div>
			<div class="space-y-1.5">
				<Label for="context-source-url">
					{m.settings_ai_sources_url_field()}
				</Label>
				<Input id="context-source-url" type="url" bind:value={url} />
			</div>
		</div>
		<div class="space-y-1.5">
			<Label for="context-source-description">
				{m.settings_ai_sources_description_field()}
			</Label>
			<Input id="context-source-description" bind:value={description} />
		</div>
		<Button type="submit" variant="outline" disabled={actions.add.isPending}>
			<Plus class="size-4" />
			{m.settings_ai_sources_add()}
		</Button>
	</form>
</div>
