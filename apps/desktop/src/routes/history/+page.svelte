<script lang="ts">
import { goto } from "$app/navigation";
import { createActions } from "$lib/actions";
import type { SearchHistory, SearchStatus } from "$lib/api/types";
import EmptyState from "$lib/components/empty-state.svelte";
import ErrorState from "$lib/components/error-state.svelte";
import ListSkeleton from "$lib/components/list-skeleton.svelte";
// noinspection ES6UnusedImports
import * as AlertDialog from "$lib/components/ui/alert-dialog";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import ExternalLink from "@lucide/svelte/icons/external-link";
import HistoryIcon from "@lucide/svelte/icons/history";
import RotateCcw from "@lucide/svelte/icons/rotate-ccw";
import { useQueryClient } from "@tanstack/svelte-query";
import { toast } from "svelte-sonner";

const queryClient = useQueryClient();
const historyQuery = query.search.history.create();
// The current active run (null when idle) — decides whether a re-launch needs
// the replace-confirm dialog.
const currentSearch = query.search.vacancies.create();
const actions = createActions(queryClient).search.vacancies;

// The run awaiting replace confirmation, and in-flight guards.
let pendingRun = $state<SearchHistory | null>(null);
let dialogOpen = $state(false);
let relaunchingId = $state<string | null>(null);
let replacing = $state(false);

const busy = $derived(relaunchingId !== null || replacing);

type BadgeVariant = "default" | "secondary" | "destructive" | "ghost";

function statusLabel(status: SearchStatus): string {
	switch (status) {
		case "pending":
			return m.status_pending();
		case "running":
			return m.status_running();
		case "canceled":
			return m.status_canceled();
		case "exited":
			return m.status_exited();
		case "failed":
			return m.status_failed();
		case "interrupted":
			return m.status_interrupted();
		default:
			return m.status_unknown();
	}
}

function statusVariant(status: SearchStatus): BadgeVariant {
	switch (status) {
		case "exited":
			return "default";
		case "failed":
			return "destructive";
		case "canceled":
		case "interrupted":
			return "ghost";
		default:
			// pending / running
			return "secondary";
	}
}

function formatDate(iso: string | null): string {
	if (!iso) return "—";
	return new Date(iso).toLocaleString();
}

async function doStart(run: SearchHistory) {
	relaunchingId = run.id;
	try {
		await actions.start.mutateAsync({
			url: run.url,
			maxPages: run.max_pages,
			maxVacancies: run.max_vacancies,
		});
		toast.success(m.history_relaunch_success());
		await goto("/queue");
	} catch (e) {
		const error = e instanceof Error ? e.message : "unknown";
		toast.error(m.history_relaunch_failed({ error }));
	} finally {
		relaunchingId = null;
	}
}

function relaunch(run: SearchHistory) {
	// A search is already running → confirm replacing it, mirroring the
	// queue page's "Запустить новый поиск?" flow.
	if (currentSearch.data) {
		pendingRun = run;
		dialogOpen = true;
		return;
	}
	doStart(run);
}

async function confirmReplace() {
	if (!pendingRun) return;
	const run = pendingRun;
	const current = currentSearch.data;
	replacing = true;
	try {
		if (current) {
			await actions.cancel.mutateAsync({ searchId: current.search_id });
		}
		dialogOpen = false;
		await doStart(run);
	} catch (e) {
		const error = e instanceof Error ? e.message : "unknown";
		toast.error(m.history_relaunch_failed({ error }));
	} finally {
		replacing = false;
		pendingRun = null;
	}
}
</script>

<AlertDialog.Root bind:open={dialogOpen}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>{m.dialog_replace_title()}</AlertDialog.Title>
            <AlertDialog.Description>
                {m.dialog_replace_description()}
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>{m.dialog_replace_cancel()}</AlertDialog.Cancel>
            <AlertDialog.Action onclick={confirmReplace} disabled={busy}>
                {replacing ? m.dialog_replace_confirming() : m.dialog_replace_confirm()}
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<div class="container mx-auto max-w-2xl p-6 space-y-6">
    <h1 class="text-2xl font-semibold">{m.history_title()}</h1>

    {#if historyQuery.isPending}
        <ListSkeleton/>
    {:else if historyQuery.isError}
        <ErrorState
                message={m.history_error_load({
                    error: historyQuery.error?.message ?? "unknown error",
                })}
                onRetry={() => historyQuery.refetch()}
        />
    {:else if historyQuery.data.length === 0}
        <EmptyState icon={HistoryIcon} title={m.history_empty()}/>
    {:else}
        <ul class="space-y-3">
            {#each historyQuery.data as run (run.id)}
                <li
                        class="bg-card text-card-foreground flex items-start gap-4 rounded-lg border p-4"
                >
                    <div class="min-w-0 flex-1 space-y-1">
                        <div class="flex items-center gap-2">
                            <Badge variant={statusVariant(run.status)}>
                                {statusLabel(run.status)}
                            </Badge>
                            <a
                                    href={run.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    aria-label={m.queue_card_open_external()}
                                    class="text-muted-foreground hover:text-foreground inline-flex min-w-0 items-center gap-1 text-sm"
                            >
                                <span class="truncate">{run.url}</span>
                                <ExternalLink class="size-3.5 shrink-0"/>
                            </a>
                        </div>
                        <p class="text-sm">
                            {m.history_parsed({
                                vacancies: run.parsed_vacancies ?? 0,
                                pages: run.parsed_pages ?? 0,
                            })}
                        </p>
                        <p class="text-muted-foreground text-xs">
                            {m.history_started({ date: formatDate(run.started_at) })}
                            {#if run.finished_at}
                                · {m.history_finished({ date: formatDate(run.finished_at) })}
                            {/if}
                        </p>
                        {#if run.error}
                            <p class="text-destructive text-xs">{run.error}</p>
                        {/if}
                    </div>
                    <Button
                            variant="outline"
                            size="sm"
                            class="shrink-0"
                            onclick={() => relaunch(run)}
                            disabled={busy}
                    >
                        <RotateCcw class="size-4"/>
                        {relaunchingId === run.id
                            ? m.history_relaunching()
                            : m.history_relaunch()}
                    </Button>
                </li>
            {/each}
        </ul>
    {/if}
</div>
