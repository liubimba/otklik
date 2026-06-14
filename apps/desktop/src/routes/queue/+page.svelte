<script lang="ts">
import * as AlertDialog from "$lib/components/ui/alert-dialog/index.js";

import { deleteSearchVacancies } from "$lib/api/client";
import { Button } from "$lib/components/ui/button";
import {
	createCurrentSearchQuery,
	currentSearchQueryKey,
} from "$lib/queries/search";
import { createSettingsQuery } from "$lib/queries/settings";
import { createVacanciesQuery } from "$lib/queries/vacancies";
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
		toast.error(`Не удалось отменить поиск: ${e.message}`);
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
            <AlertDialog.Title>Запустить новый поиск?</AlertDialog.Title>
            <AlertDialog.Description>
                Текущий поиск будет отменён. Уже спарсенные вакансии останутся в
                очереди.
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>Не отменять</AlertDialog.Cancel>
            <AlertDialog.Action
                onclick={handleConfirmReplace}
                disabled={cancelSearchMutation.isPending}
            >
                {cancelSearchMutation.isPending
                    ? "Отменяем…"
                    : "Отменить и запустить новый"}
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<main class="container mx-auto p-6 space-y-6 relative">
    <header class="flex items-center justify-between sticky top-0">
        <h1 class="text-2xl font-bold">Очередь вакансий</h1>
        {#if currentSearch.data}
            <span>Pages:{currentSearch.data.parsed_pages}</span>
            <span>Vacancies:{currentSearch.data.parsed_vacancies}</span>
            <span>Status:{currentSearch.data.status}</span>
        {/if}
        <Button onclick={handleStart} disabled={!isInactive}>
            {#if currentSearch.data?.status == "running" || currentSearch.data?.status == "pending"}
                Отменить поиск
            {:else}
                Новый поиск
            {/if}
        </Button>
    </header>

    {#if searchPicker.state.status !== "idle"}
        <section class="border rounded-lg p-4 space-y-3 bg-muted/30">
            {#if searchPicker.state.status === "opening_session"}
                <p class="text-sm">Открываем hh.ru в браузере…</p>
            {:else if searchPicker.state.status === "awaiting_confirm"}
                <div class="space-y-2">
                    <p class="font-medium">
                        Настройте фильтр в открытой вкладке
                    </p>
                    <p class="text-sm text-muted-foreground">
                        Перейдите во вкладку Chromium, отфильтруйте вакансии
                        нужным образом (регион, опыт, формат и т.д.) и вернитесь
                        сюда. Поиск пойдёт по тому URL, который будет в адресной
                        строке вкладки на момент подтверждения.
                    </p>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <label class="flex flex-col gap-1 text-sm">
                        <span>Макс. страниц</span>
                        <input
                            type="number"
                            min="1"
                            bind:value={maxPagesInput}
                            placeholder={settings.data
                                ? String(settings.data.search.max_pages)
                                : "из настроек"}
                            class="border rounded px-2 py-1"
                        />
                    </label>
                    <label class="flex flex-col gap-1 text-sm">
                        <span>Макс. вакансий</span>
                        <input
                            type="number"
                            min="1"
                            bind:value={maxVacanciesInput}
                            placeholder={settings.data
                                ? String(settings.data.search.max_vacancies)
                                : "из настроек"}
                            class="border rounded px-2 py-1"
                        />
                    </label>
                </div>
                <div class="flex gap-2">
                    <Button onclick={handleConfirm}>Подтвердить</Button>
                    <Button variant="outline" onclick={handleCancel}>
                        Отмена
                    </Button>
                </div>
            {:else if searchPicker.state.status === "confirming"}
                <p class="text-sm">Подтверждаем выбор…</p>
            {:else if searchPicker.state.status === "starting_search"}
                <p class="text-sm">Запускаем поиск…</p>
            {:else if searchPicker.state.status === "canceling"}
                <p class="text-sm">Отменяем сессию…</p>
            {:else if searchPicker.state.status === "error"}
                <div class="space-y-2">
                    <p class="font-medium text-destructive">
                        Ошибка: {searchPicker.state.message}
                    </p>
                    <Button variant="outline" onclick={handleDismissError}>
                        Закрыть
                    </Button>
                </div>
            {/if}
        </section>
    {/if}

    {#if vacancies.isPending}
        <p>Загрузка…</p>
    {:else if vacancies.isError}
        <p class="text-red-600">
            Не удалось загрузить вакансии: {vacancies.error?.message ??
                "unknown error"}
        </p>
    {:else if vacancies.data.length === 0 && !isSearchInFlight}
        <p class="text-gray-500">
            Пока пусто. Нажмите «Новый поиск», чтобы запустить парсинг.
        </p>
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
