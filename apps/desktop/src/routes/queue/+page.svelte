<script lang="ts">
import * as AlertDialog from "$lib/components/ui/alert-dialog/index.js";

import { deleteSearchVacancies } from "$lib/api/client";
import type { SearchStatus } from "$lib/api/types";
import { Button } from "$lib/components/ui/button";
import * as m from "$lib/paraglide/messages";
import {
	createCurrentSearchQuery,
	currentSearchQueryKey,
} from "$lib/queries/search";
import { createSettingsQuery } from "$lib/queries/settings";
import {
	createVacanciesQuery,
	vacanciesQueryKey,
} from "$lib/queries/vacancies";
import { searchPicker } from "$lib/stores/search_picker.svelte";
import { createMutation, useQueryClient } from "@tanstack/svelte-query";
import { toast } from "svelte-sonner";

const queryClient = useQueryClient();
const currentSearch = createCurrentSearchQuery();

let replaceDialogOpen = $state(false);

const cancelSearchMutation = createMutation(() => ({
	mutationFn: (search_id: string) => deleteSearchVacancies(search_id),
	onSuccess: () => {
		queryClient.setQueryData(currentSearchQueryKey, null);
	},
	onError: (e: Error) => {
		toast.error(m.toast_cancel_failed({ error: e.message }));
	},
}));

const vacancies = createVacanciesQuery();
const settings = createSettingsQuery();

let maxPagesInput = $state<string>("");
let maxVacanciesInput = $state<string>("");

$effect(() => {
	if (searchPicker.state.status === "error") {
		toast.error(searchPicker.state.message);
	}
});

const parseOptionalInt = (raw: string): number | null => {
	const trimmed = raw.trim();
	if (trimmed === "") return null;
	const n = Number(trimmed);
	return Number.isFinite(n) && n > 0 ? Math.floor(n) : null;
};

const statusLabel = (status: SearchStatus): string => {
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
	}
};

const handleStart = () => {
	if (currentSearch.data) {
		replaceDialogOpen = true;
		return;
	}
	searchPicker.startNewSession();
};

const handleConfirmReplace = async () => {
	const current = currentSearch.data;
	if (!current) {
		replaceDialogOpen = false;
		return;
	}
	try {
		await cancelSearchMutation.mutateAsync(current.search_id);
		replaceDialogOpen = false;
		await searchPicker.startNewSession();
	} catch {
		replaceDialogOpen = false;
	}
};

const handleConfirm = async () => {
	const max_pages = parseOptionalInt(maxPagesInput);
	const max_vacancies = parseOptionalInt(maxVacanciesInput);
	const search = await searchPicker.confirmSession(max_pages, max_vacancies);
	if (search) {
		queryClient.setQueryData(currentSearchQueryKey, search);
		queryClient.invalidateQueries({ queryKey: vacanciesQueryKey });
	}
};

const handleCancel = () => searchPicker.cancelSession();

const handleDismissError = () => {
	maxPagesInput = "";
	maxVacanciesInput = "";
	searchPicker.clearError();
};

const isInactive = $derived(
	searchPicker.state.status === "idle" || searchPicker.state.status === "error",
);

const isSearchInFlight = $derived(
	currentSearch.data?.status === "running" ||
		currentSearch.data?.status === "pending",
);
</script>

<AlertDialog.Root bind:open={replaceDialogOpen}>
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
                onclick={handleConfirmReplace}
                disabled={cancelSearchMutation.isPending}
            >
                {cancelSearchMutation.isPending
                    ? m.dialog_replace_confirming()
                    : m.dialog_replace_confirm()}
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<main class="container mx-auto p-6 space-y-6 relative">
    <header class="flex items-center justify-between sticky top-0">
        <h1 class="text-2xl font-bold">{m.queue_title()}</h1>
        {#if currentSearch.data}
            <span>{m.queue_header_pages({ n: currentSearch.data.parsed_pages })}</span>
            <span>{m.queue_count({ count: currentSearch.data.parsed_vacancies })}</span>
            <span>{m.queue_header_status({ status: statusLabel(currentSearch.data.status) })}</span>
        {/if}
        <Button onclick={handleStart} disabled={!isInactive}>
            {#if isSearchInFlight}
                {m.queue_button_cancel_search()}
            {:else}
                {m.queue_button_new_search()}
            {/if}
        </Button>
    </header>

    {#if searchPicker.state.status !== "idle"}
        <section class="border rounded-lg p-4 space-y-3 bg-muted/30">
            {#if searchPicker.state.status === "opening_session"}
                <p class="text-sm">{m.picker_opening()}</p>
            {:else if searchPicker.state.status === "awaiting_confirm"}
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
                            bind:value={maxPagesInput}
                            placeholder={settings.data
                                ? String(settings.data.search.max_pages)
                                : m.picker_placeholder_from_settings()}
                            class="border rounded px-2 py-1"
                        />
                    </label>
                    <label class="flex flex-col gap-1 text-sm">
                        <span>{m.picker_max_vacancies()}</span>
                        <input
                            type="number"
                            min="1"
                            bind:value={maxVacanciesInput}
                            placeholder={settings.data
                                ? String(settings.data.search.max_vacancies)
                                : m.picker_placeholder_from_settings()}
                            class="border rounded px-2 py-1"
                        />
                    </label>
                </div>
                <div class="flex gap-2">
                    <Button onclick={handleConfirm}>{m.picker_button_confirm()}</Button>
                    <Button variant="outline" onclick={handleCancel}>
                        {m.picker_button_cancel()}
                    </Button>
                </div>
            {:else if searchPicker.state.status === "confirming"}
                <p class="text-sm">{m.picker_confirming()}</p>
            {:else if searchPicker.state.status === "starting_search"}
                <p class="text-sm">{m.picker_starting()}</p>
            {:else if searchPicker.state.status === "canceling"}
                <p class="text-sm">{m.picker_canceling()}</p>
            {:else if searchPicker.state.status === "error"}
                <div class="space-y-2">
                    <p class="font-medium text-destructive">
                        {m.picker_error_prefix({ message: searchPicker.state.message })}
                    </p>
                    <Button variant="outline" onclick={handleDismissError}>
                        {m.picker_button_dismiss()}
                    </Button>
                </div>
            {/if}
        </section>
    {/if}

    {#if vacancies.isPending}
        <p>{m.queue_loading()}</p>
    {:else if vacancies.isError}
        <p class="text-red-600">
            {m.queue_error_load({ error: vacancies.error?.message ?? "unknown error" })}
        </p>
    {:else if vacancies.data.length === 0 && !isSearchInFlight}
        <p class="text-gray-500">{m.queue_empty()}</p>
    {:else}
        <ul class="space-y-3">
            {#if isSearchInFlight}
                <li class="border rounded p-4 space-y-2">
                    <div class="h-6 w-3/4 bg-muted animate-pulse rounded"></div>
                    <div class="h-4 w-1/3 bg-muted animate-pulse rounded"></div>
                    <div class="h-4 w-1/4 bg-muted animate-pulse rounded"></div>
                </li>
            {/if}
            {#each vacancies.data as vacancy (vacancy.id)}
                <li class="border rounded p-4">
                    <a
                        href={vacancy.apply_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-lg font-medium hover:underline"
                    >
                        {vacancy.title}
                    </a>
                    {#if vacancy.company_name}
                        <p class="text-sm text-gray-700">
                            {vacancy.company_name}
                        </p>
                    {/if}
                    {#if vacancy.salary}
                        <p class="text-sm">{vacancy.salary}</p>
                    {/if}
                    {#if vacancy.work_location}
                        <p class="text-sm text-gray-600">
                            {vacancy.work_location}
                        </p>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
</main>
