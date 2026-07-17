<script lang="ts">
import type { VacancyStatusFilter } from "$lib/api/types";
import EmptyState from "$lib/components/empty-state.svelte";
import ErrorState from "$lib/components/error-state.svelte";
import ListSkeleton from "$lib/components/list-skeleton.svelte";
import { Button } from "$lib/components/ui/button";
import { Input } from "$lib/components/ui/input";
import VacancyCard from "$lib/components/vacancy-card.svelte";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import { store } from "$lib/stores";
import Briefcase from "@lucide/svelte/icons/briefcase";
import Search from "@lucide/svelte/icons/search";
import SearchX from "@lucide/svelte/icons/search-x";
import X from "@lucide/svelte/icons/x";

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

const FILTERS: { value: VacancyStatusFilter; label: () => string }[] = [
	{ value: "none", label: m.vacancies_filter_none },
	{ value: "letter_pending", label: m.card_status_letter_pending },
	{ value: "letter_ready", label: m.card_status_letter_ready },
	{ value: "letter_reviewing", label: m.card_status_letter_reviewing },
	{ value: "letter_sending", label: m.card_status_letter_sending },
	{ value: "letter_sent", label: m.card_status_letter_sent },
	{ value: "error", label: m.card_status_error },
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

const vacanciesQuery = query.all_vacancies.create(
	() => activeFilters,
	() => search,
	() => limit,
);

const items = $derived(vacanciesQuery.data?.items ?? []);
const total = $derived(vacanciesQuery.data?.total ?? 0);
const hasMore = $derived(items.length < total);
const loadingMore = $derived(vacanciesQuery.isFetching && items.length > 0);
const isFiltered = $derived(activeFilters.length > 0 || search.trim() !== "");

function toggle(value: VacancyStatusFilter) {
	activeFilters = activeFilters.includes(value)
		? activeFilters.filter((filter) => filter !== value)
		: [...activeFilters, value];
	limit = PAGE_SIZE;
}

function clearFilters() {
	if (activeFilters.length === 0) return;
	activeFilters = [];
	limit = PAGE_SIZE;
}

function clearSearch() {
	searchInput = "";
	search = "";
	limit = PAGE_SIZE;
}

function clearAll() {
	activeFilters = [];
	clearSearch();
}
</script>

<div class="container mx-auto max-w-2xl p-6 space-y-6">
    <div class="flex items-baseline justify-between gap-4">
        <h1 class="text-2xl font-semibold">{m.vacancies_title()}</h1>
        {#if vacanciesQuery.data}
            <span class="text-muted-foreground text-sm">
                {m.vacancies_total({ total })}
            </span>
        {/if}
    </div>

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
                    onclick={() => toggle(filter.value)}
            >
                {filter.label()}
            </Button>
        {/each}
    </div>

    {#if vacanciesQuery.isPending}
        <ListSkeleton/>
    {:else if vacanciesQuery.isError}
        <ErrorState
                message={m.vacancies_error_load({
                    error: vacanciesQuery.error?.message ?? "unknown error",
                })}
                onRetry={() => vacanciesQuery.refetch()}
        />
    {:else if items.length === 0}
        {#if isFiltered}
            <EmptyState icon={SearchX} title={m.vacancies_empty_filtered()}>
                <Button variant="outline" size="sm" onclick={clearAll}>
                    {m.vacancies_filter_all()}
                </Button>
            </EmptyState>
        {:else}
            <EmptyState icon={Briefcase} title={m.vacancies_empty()}/>
        {/if}
    {:else}
        <ul class="space-y-3">
            {#each items as vacancy (vacancy.id)}
                <li>
                    <VacancyCard
                            {vacancy}
                            status={vacancy.status}
                            onclick={(v) => store.letter.review.open(v.id)}
                    />
                </li>
            {/each}
        </ul>

        {#if hasMore}
            <div class="flex justify-center">
                <Button
                        variant="outline"
                        onclick={() => (limit += PAGE_SIZE)}
                        disabled={loadingMore}
                >
                    {loadingMore ? m.vacancies_loading_more() : m.vacancies_load_more()}
                </Button>
            </div>
        {/if}
    {/if}
</div>
