<script lang="ts">
import { createActions } from "$lib/actions";
import type { VacancyStatusFilter } from "$lib/api/types";
import EmptyState from "$lib/components/empty-state.svelte";
import ErrorState from "$lib/components/error-state.svelte";
import ListSkeleton from "$lib/components/list-skeleton.svelte";
import LiveStatus from "$lib/components/live-status.svelte";
import * as AlertDialog from "$lib/components/ui/alert-dialog";
import { Button } from "$lib/components/ui/button";
import { Input } from "$lib/components/ui/input";
import { Switch } from "$lib/components/ui/switch";
import VacancyCard from "$lib/components/vacancy-card.svelte";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import { store } from "$lib/stores";
import { letterReview } from "$lib/stores/letter_review.svelte";
import Inbox from "@lucide/svelte/icons/inbox";
import Pause from "@lucide/svelte/icons/pause";
import Play from "@lucide/svelte/icons/play";
import RotateCcw from "@lucide/svelte/icons/rotate-ccw";
import Search from "@lucide/svelte/icons/search";
import SearchX from "@lucide/svelte/icons/search-x";
import Send from "@lucide/svelte/icons/send";
import X from "@lucide/svelte/icons/x";
import { useQueryClient } from "@tanstack/svelte-query";
import { toast } from "svelte-sonner";
import { createSearchPageView } from "./search.view.svelte";
import { createSearchPageViewModel } from "./search.view_model.svelte";

const queryClient = useQueryClient();
const actions = createActions(queryClient);

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

const FILTERS: { value: VacancyStatusFilter; label: () => string }[] = [
	{ value: "none", label: m.vacancies_filter_none },
	{ value: "letter_pending", label: m.card_status_letter_pending },
	{ value: "letter_ready", label: m.card_status_letter_ready },
	{ value: "letter_reviewing", label: m.card_status_letter_reviewing },
	{ value: "letter_queued", label: m.card_status_letter_queued },
	{ value: "letter_sending", label: m.card_status_letter_sending },
	{ value: "letter_sent", label: m.card_status_letter_sent },
	{ value: "error", label: m.card_status_error },
	{ value: "interrupted", label: m.card_status_interrupted },
	{ value: "already_applied", label: m.card_status_already_applied },
	{ value: "skipped", label: m.card_status_skipped },
];

let activeFilters = $state<VacancyStatusFilter[]>([]);
let searchInput = $state("");
let search = $state("");
let limit = $state(PAGE_SIZE);

$effect(() => {
	const next = searchInput;
	const timer = setTimeout(() => {
		if (next === search) return;
		search = next;
		limit = PAGE_SIZE;
	}, SEARCH_DEBOUNCE_MS);
	return () => clearTimeout(timer);
});

function toggleFilter(value: VacancyStatusFilter) {
	activeFilters = activeFilters.includes(value)
		? activeFilters.filter((f) => f !== value)
		: [...activeFilters, value];
	limit = PAGE_SIZE;
}

function clearFilters() {
	activeFilters = [];
	limit = PAGE_SIZE;
}

function clearSearch() {
	searchInput = "";
	search = "";
	limit = PAGE_SIZE;
}

const settingsQuery = query.settings.create();
const vacanciesQuery = query.all_vacancies.create(
	() => activeFilters,
	() => search,
	() => limit,
	() => "latest",
);
const searchQuery = query.search.vacancies.create();
const restartCountsQuery = query.restart_counts.create();

const vacancyItems = $derived(vacanciesQuery.data?.items ?? []);
const vacancyTotal = $derived(vacanciesQuery.data?.total ?? 0);
const hasMoreVacancies = $derived(vacancyItems.length < vacancyTotal);
const loadingMoreVacancies = $derived(
	vacanciesQuery.isFetching && vacancyItems.length > 0,
);
const vacanciesFiltered = $derived(
	activeFilters.length > 0 || search.trim() !== "",
);

const model = createSearchPageViewModel(searchQuery);
const view = createSearchPageView(searchQuery, actions, model);

const autoGenerate = $derived(settingsQuery.data?.user.auto_generate ?? false);
const autoSubmit = $derived(settingsQuery.data?.user.auto_submit ?? false);
const generationCount = $derived(restartCountsQuery.data?.generation ?? 0);
const submissionCount = $derived(restartCountsQuery.data?.submission ?? 0);
const savingAuto = $derived(actions.settings.updateUser.isPending);
const restartingGeneration = $derived(
	actions.applications.restartGeneration.isPending,
);
const restartingSubmission = $derived(
	actions.applications.restartSubmission.isPending,
);
const togglingSearch = $derived(
	actions.search.vacancies.pause.isPending ||
		actions.search.vacancies.resume.isPending,
);

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
    <header class="flex items-center justify-between gap-3">
        <h1 class="text-2xl font-semibold">{m.queue_title()}</h1>
        <div class="flex items-center gap-2">
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
            {#if model.search.vacancies.inFlight}
                <Button
                        variant="outline"
                        size="icon"
                        onclick={view.search.vacancies.pauseResume}
                        disabled={togglingSearch}
                        aria-label={model.search.vacancies.paused
                        ? m.queue_button_resume_search()
                        : m.queue_button_pause_search()}
                        title={model.search.vacancies.paused
                        ? m.queue_button_resume_search()
                        : m.queue_button_pause_search()}
                >
                    {#if model.search.vacancies.paused}
                        <Play class="size-4"/>
                    {:else}
                        <Pause class="size-4"/>
                    {/if}
                </Button>
            {/if}
            <Button onclick={view.search.filter.start} disabled={!model.search.filter.inactive}>
                {#if model.search.vacancies.inFlight}
                    {m.queue_button_cancel_search()}
                {:else}
                    {m.queue_button_new_search()}
                {/if}
            </Button>
        </div>
    </header>

    <section class="bg-card rounded-lg border text-sm">
        <div class="flex items-center justify-between gap-3 px-4 py-3">
            <div class="flex items-center gap-2.5">
                <Switch
                        checked={autoGenerate}
                        disabled={savingAuto || !settingsQuery.data}
                        onCheckedChange={view.auto.toggleGenerate}
                        aria-label={m.queue_auto_generate_label()}
                />
                <span>{m.queue_auto_generate_label()}</span>
            </div>
            {#if autoGenerate && generationCount > 0}
                <Button
                        variant="ghost"
                        size="sm"
                        class="text-muted-foreground"
                        onclick={view.applications.restartGeneration}
                        disabled={restartingGeneration}
                >
                    <RotateCcw class="size-3.5"/>
                    {m.queue_restart_generation({ count: generationCount })}
                </Button>
            {/if}
        </div>
        <div
                class="flex items-center justify-between gap-3 border-t px-4 py-3 {autoGenerate
                ? ''
                : 'opacity-50'}"
        >
            <div class="flex items-center gap-2.5">
                <Switch
                        checked={autoSubmit}
                        disabled={!autoGenerate || savingAuto || !settingsQuery.data}
                        onCheckedChange={view.auto.toggleSubmit}
                        aria-label={m.queue_auto_submit_label()}
                />
                <span>{m.queue_auto_submit_label()}</span>
            </div>
            {#if autoSubmit && submissionCount > 0}
                <Button
                        variant="ghost"
                        size="sm"
                        class="text-muted-foreground"
                        onclick={view.applications.restartSubmission}
                        disabled={restartingSubmission}
                >
                    <Send class="size-3.5"/>
                    {m.queue_restart_submission({ count: submissionCount })}
                </Button>
            {/if}
        </div>
    </section>

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

    <div class="relative">
        <Search
                class="text-muted-foreground pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2"
        />
        <Input
                type="search"
                bind:value={searchInput}
                placeholder={m.vacancies_search_placeholder()}
                aria-label={m.vacancies_search_placeholder()}
                class="pl-9 pr-9"
        />
        {#if searchInput}
            <button
                    type="button"
                    onclick={clearSearch}
                    aria-label={m.vacancies_search_clear()}
                    class="text-muted-foreground hover:text-foreground focus-visible:ring-ring/40 absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 focus-visible:outline-none focus-visible:ring-2"
            >
                <X class="size-4"/>
            </button>
        {/if}
    </div>

    <div class="flex flex-wrap gap-2">
        <Button
                variant={activeFilters.length === 0 ? "default" : "outline"}
                size="sm"
                onclick={clearFilters}
        >
            {m.vacancies_filter_all()}
        </Button>
        {#each FILTERS as filter (filter.value)}
            <Button
                    variant={activeFilters.includes(filter.value) ? "default" : "outline"}
                    size="sm"
                    aria-pressed={activeFilters.includes(filter.value)}
                    onclick={() => toggleFilter(filter.value)}
            >
                {filter.label()}
            </Button>
        {/each}
    </div>

    {#if vacanciesQuery.isPending}
        <ListSkeleton/>
    {:else if vacanciesQuery.isError}
        <ErrorState
                message={m.queue_error_load({
                    error: vacanciesQuery.error?.message ?? "unknown error",
                })}
                onRetry={() => vacanciesQuery.refetch()}
        />
    {:else if vacancyItems.length === 0 && !model.search.vacancies.inFlight}
        {#if vacanciesFiltered}
            <EmptyState icon={SearchX} title={m.vacancies_empty_filtered()}>
                <Button
                        variant="outline"
                        size="sm"
                        onclick={() => {
                        clearFilters();
                        clearSearch();
                    }}
                >
                    {m.vacancies_filter_all()}
                </Button>
            </EmptyState>
        {:else}
            <EmptyState icon={Inbox} title={m.queue_empty()}>
                <Button onclick={view.search.filter.start} disabled={!model.search.filter.inactive}>
                    {m.queue_button_new_search()}
                </Button>
            </EmptyState>
        {/if}
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
            {#each vacancyItems as vacancy (vacancy.id)}
                <li>
                    <VacancyCard
                            {vacancy}
                            status={vacancy.status}
                            onclick={(v) => letterReview.open(v.id)}
                    />
                </li>
            {/each}
        </ul>

        {#if hasMoreVacancies}
            <div class="flex justify-center">
                <Button
                        variant="outline"
                        onclick={() => (limit += PAGE_SIZE)}
                        disabled={loadingMoreVacancies}
                >
                    {loadingMoreVacancies
                        ? m.vacancies_loading_more()
                        : m.vacancies_load_more()}
                </Button>
            </div>
        {/if}
    {/if}
</div>
