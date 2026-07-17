<script lang="ts">
import { createActions } from "$lib/actions";
import EmptyState from "$lib/components/empty-state.svelte";
import ErrorState from "$lib/components/error-state.svelte";
import ListSkeleton from "$lib/components/list-skeleton.svelte";
import LiveStatus from "$lib/components/live-status.svelte";
import * as AlertDialog from "$lib/components/ui/alert-dialog";
import { Button } from "$lib/components/ui/button";
import VacancyCard from "$lib/components/vacancy-card.svelte";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import { store } from "$lib/stores";
import { letterReview } from "$lib/stores/letter_review.svelte";
import Inbox from "@lucide/svelte/icons/inbox";
import { useQueryClient } from "@tanstack/svelte-query";
import { toast } from "svelte-sonner";
import { createSearchPageView } from "./search.view.svelte";
import { createSearchPageViewModel } from "./search.view_model.svelte";

const queryClient = useQueryClient();
const actions = createActions(queryClient);

const settingsQuery = query.settings.create();
const vacanciesQuery = query.vacancies.create();
const searchQuery = query.search.vacancies.create();

const model = createSearchPageViewModel(searchQuery);
const view = createSearchPageView(searchQuery, actions, model);

const liveStatus = $derived.by(() => {
	const picker = store.search.filter.state;
	switch (picker.status) {
		case "opening_session":
			return m.picker_opening();
		case "confirming":
			return m.picker_confirming();
		case "starting_search":
			return m.picker_starting();
		case "canceling":
			return m.picker_canceling();
		case "error":
			return m.picker_error_prefix({ message: picker.message ?? "" });
	}
	if (!searchQuery.data) return "";
	return `${m.queue_header_status({ status: model.search.vacancies.status })} · ${m.queue_count(
		{ count: searchQuery.data.parsed_vacancies ?? 0 },
	)}`;
});

$effect(() => {
	if (actions.search.filter.cancel.isError) {
		toast.error(
			m.toast_cancel_failed({
				error: actions.search.filter.cancel.error.message,
			}),
		);
	}
});
</script>

<AlertDialog.Root bind:open={model.dialog.search.filter.active}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>{m.dialog_replace_title()}</AlertDialog.Title>
            <AlertDialog.Description>
                {m.dialog_replace_description()}
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>{m.dialog_replace_cancel()}</AlertDialog.Cancel>
            <AlertDialog.Action
                    onclick={view.search.filter.dialog.replace}
                    disabled={actions.search.filter.cancel.isPending}
            >
                {actions.search.filter.cancel.isPending
                    ? m.dialog_replace_confirming()
                    : m.dialog_replace_confirm()}
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<div class="container mx-auto max-w-2xl p-6 space-y-6 relative">
    <header class="flex items-center justify-between sticky top-0">
        <h1 class="text-2xl font-semibold">{m.queue_title()}</h1>
        {#if searchQuery.data}
            <span class="text-muted-foreground font-mono text-xs"
            >{m.queue_header_pages({
                n: searchQuery.data.parsed_pages ?? 0,
            })}</span
            >
            <span class="text-muted-foreground font-mono text-xs"
            >{m.queue_count({
                count: searchQuery.data.parsed_vacancies ?? 0,
            })}</span
            >
            <span class="text-muted-foreground font-mono text-xs"
            >{m.queue_header_status({
                status: model.search.vacancies.status
            })}</span
            >
        {/if}
        <Button onclick={view.search.filter.start} disabled={!model.search.filter.inactive}>
            {#if model.search.vacancies.inFlight}
                {m.queue_button_cancel_search()}
            {:else}
                {m.queue_button_new_search()}
            {/if}
        </Button>
    </header>

    {#if store.search.filter.state.status !== "idle"}
        <section class="border rounded-lg p-4 space-y-3 bg-muted/30">
            {#if store.search.filter.state.status === "opening_session"}
                <p class="text-sm">{m.picker_opening()}</p>
            {:else if store.search.filter.state.status === "awaiting_confirm"}
                <div class="space-y-2">
                    <p class="font-medium">{m.picker_awaiting_title()}</p>
                    <p class="text-sm text-muted-foreground">
                        {m.picker_awaiting_instructions()}
                    </p>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <label class="flex flex-col gap-1 text-sm">
                        <span>{m.picker_max_pages()}</span>
                        <input
                                type="number"
                                min="1"
                                bind:value={model.search.filter.maxPages}
                                placeholder={settingsQuery.data
                                ? String(settingsQuery.data.search.max_pages)
                                : m.picker_placeholder_from_settings()}
                                class="border rounded px-2 py-1"
                        />
                    </label>
                    <label class="flex flex-col gap-1 text-sm">
                        <span>{m.picker_max_vacancies()}</span>
                        <input
                                type="number"
                                min="1"
                                bind:value={model.search.filter.maxVacancies}
                                placeholder={settingsQuery.data
                                ? String(settingsQuery.data.search.max_vacancies)
                                : m.picker_placeholder_from_settings()}
                                class="border rounded px-2 py-1"
                        />
                    </label>
                </div>
                <div class="flex gap-2">
                    <Button onclick={view.search.filter.confirm}
                    >{m.picker_button_confirm()}</Button
                    >
                    <Button variant="outline" onclick={view.search.filter.cancel}>
                        {m.picker_button_cancel()}
                    </Button>
                </div>
            {:else if store.search.filter.state.status === "confirming"}
                <p class="text-sm">{m.picker_confirming()}</p>
            {:else if store.search.filter.state.status === "starting_search"}
                <p class="text-sm">{m.picker_starting()}</p>
            {:else if store.search.filter.state.status === "canceling"}
                <p class="text-sm">{m.picker_canceling()}</p>
            {:else if store.search.filter.state.status === "error"}
                <div class="space-y-2">
                    <p class="font-medium text-destructive">
                        {m.picker_error_prefix({
                            message: store.search.filter.state.message ?? "",
                        })}
                    </p>
                    <Button variant="outline" onclick={view.search.filter.dismissError}>
                        {m.picker_button_dismiss()}
                    </Button>
                </div>
            {/if}
        </section>
    {/if}

    <LiveStatus text={liveStatus}/>

    {#if vacanciesQuery.isPending}
        <ListSkeleton/>
    {:else if vacanciesQuery.isError}
        <ErrorState
                message={m.queue_error_load({
                    error: vacanciesQuery.error?.message ?? "unknown error",
                })}
                onRetry={() => vacanciesQuery.refetch()}
        />
    {:else if vacanciesQuery.data.length === 0 && !model.search.vacancies.inFlight}
        <EmptyState icon={Inbox} title={m.queue_empty()}>
            <Button onclick={view.search.filter.start} disabled={!model.search.filter.inactive}>
                {m.queue_button_new_search()}
            </Button>
        </EmptyState>
    {:else}
        <ul class="space-y-3" aria-busy={model.search.vacancies.inFlight}>
            {#if model.search.vacancies.inFlight}
                <li class="bg-card flex items-start gap-4 rounded-lg border p-4">
                    <div class="min-w-0 flex-1 space-y-2">
                        <div class="h-5 w-3/4 bg-muted animate-pulse rounded"></div>
                        <div class="h-4 w-1/3 bg-muted animate-pulse rounded"></div>
                        <div class="h-4 w-1/4 bg-muted animate-pulse rounded"></div>
                    </div>
                </li>
            {/if}
            {#each vacanciesQuery.data as vacancy (vacancy.id)}
                <li>
                    <VacancyCard
                            {vacancy}
                            onclick={(v) => letterReview.open(v.id)}
                    />
                </li>
            {/each}
        </ul>
    {/if}
</div>
