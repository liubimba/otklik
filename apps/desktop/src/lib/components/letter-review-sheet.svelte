<script lang="ts">
import {
	generateCoverLetter,
	queueForLetter,
	retryApplication,
	saveCoverLetter,
	skipApplication,
	submitApplication,
} from "$lib/api/client";
import type { CoverLetter, Vacancy } from "$lib/api/types";
import * as AlertDialog from "$lib/components/ui/alert-dialog";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import { ScrollArea } from "$lib/components/ui/scroll-area";
import * as Sheet from "$lib/components/ui/sheet";
import { Skeleton } from "$lib/components/ui/skeleton";
import * as Tabs from "$lib/components/ui/tabs";
import { Textarea } from "$lib/components/ui/textarea";
import { m } from "$lib/paraglide/messages";
import {
	applicationStatusQueryKey,
	coverLettersHistoryQueryKey,
	createApplicationStatusQuery,
	createCoverLettersHistoryQuery,
	createLatestCoverLetterQuery,
	latestCoverLetterQueryKey,
} from "$lib/queries/applications";
import { vacanciesQueryKey } from "$lib/queries/vacancies";
import { letterReview } from "$lib/stores/letter_review.svelte";
import { useQueryClient } from "@tanstack/svelte-query";
import { toast } from "svelte-sonner";

const queryClient = useQueryClient();

const applicationStatus = createApplicationStatusQuery(
	() => letterReview.vacancyId,
);
const latestCoverLetter = createLatestCoverLetterQuery(
	() => letterReview.vacancyId,
);
const coverLettersHistory = createCoverLettersHistoryQuery(
	() => letterReview.vacancyId,
);

let activeTab = $state<"letter" | "history">("letter");
let localText = $state("");
let lastSyncedVersion = $state<number | null>(null);
let restoreCandidate = $state<CoverLetter | null>(null);
let isGenerating = $state(false);
let isSaving = $state(false);
let isSubmitting = $state(false);
let isSkipping = $state(false);
let isRetrying = $state(false);

$effect(() => {
	const id = letterReview.vacancyId;
	const latest = latestCoverLetter.data;
	if (id === null) {
		localText = "";
		lastSyncedVersion = null;
		activeTab = "letter";
		return;
	}
	if (latest && latest.version !== lastSyncedVersion) {
		localText = latest.text;
		lastSyncedVersion = latest.version;
	}
});

const status = $derived(applicationStatus.data?.status ?? "parsed");
const hasApplication = $derived(
	applicationStatus.data !== null && applicationStatus.data !== undefined,
);
const isLoading = $derived(
	applicationStatus.isPending || latestCoverLetter.isPending,
);
const isErrorState = $derived(
	applicationStatus.isError || latestCoverLetter.isError,
);
const isDirty = $derived(
	latestCoverLetter.data
		? localText !== latestCoverLetter.data.text
		: localText.length > 0,
);
const isEditable = $derived(
	status === "letter_ready" ||
		status === "letter_reviewing" ||
		status === "error",
);
const isReadOnlyText = $derived(
	status === "letter_sending" ||
		status === "letter_sent" ||
		status === "skipped",
);

const vacancy = $derived.by((): Vacancy | null => {
	const id = letterReview.vacancyId;
	if (id === null) return null;
	const cached = queryClient.getQueryData<Vacancy[]>(vacanciesQueryKey);
	return cached?.find((v) => v.id === id) ?? null;
});

function errMsg(e: unknown): string {
	return e instanceof Error ? e.message : "unknown";
}

async function invalidateAll(vacancyId: number) {
	await Promise.all([
		queryClient.invalidateQueries({
			queryKey: applicationStatusQueryKey(vacancyId),
		}),
		queryClient.invalidateQueries({
			queryKey: latestCoverLetterQueryKey(vacancyId),
		}),
		queryClient.invalidateQueries({
			queryKey: coverLettersHistoryQueryKey(vacancyId),
		}),
	]);
}

async function handleGenerate() {
	const id = letterReview.vacancyId;
	if (id === null) return;
	isGenerating = true;
	try {
		if (!hasApplication) {
			await queueForLetter(id);
		}
		await generateCoverLetter(id);
		await invalidateAll(id);
		toast.success(m.review_generate_success());
	} catch (e) {
		toast.error(m.review_generate_failed({ error: errMsg(e) }));
	} finally {
		isGenerating = false;
	}
}

async function handleSave() {
	const id = letterReview.vacancyId;
	if (id === null) return;
	isSaving = true;
	try {
		await saveCoverLetter(id, localText);
		await invalidateAll(id);
		toast.success(m.review_save_success());
	} catch (e) {
		toast.error(m.review_save_failed({ error: errMsg(e) }));
	} finally {
		isSaving = false;
	}
}

async function handleSubmit() {
	const id = letterReview.vacancyId;
	if (id === null) return;
	if (isDirty) {
		await handleSave();
	}
	isSubmitting = true;
	try {
		await submitApplication(id);
		await invalidateAll(id);
		toast.success(m.review_submit_success());
	} catch (e) {
		toast.error(m.review_submit_failed({ error: errMsg(e) }));
	} finally {
		isSubmitting = false;
	}
}

async function handleSkip() {
	const id = letterReview.vacancyId;
	if (id === null) return;
	isSkipping = true;
	try {
		await skipApplication(id);
		await invalidateAll(id);
	} catch (e) {
		toast.error(m.review_skip_failed({ error: errMsg(e) }));
	} finally {
		isSkipping = false;
	}
}

async function handleRetry() {
	const id = letterReview.vacancyId;
	if (id === null) return;
	isRetrying = true;
	try {
		await retryApplication(id);
		await invalidateAll(id);
	} catch (e) {
		toast.error(m.review_retry_failed({ error: errMsg(e) }));
	} finally {
		isRetrying = false;
	}
}

function startRestore(version: CoverLetter) {
	restoreCandidate = version;
}

function confirmRestore() {
	if (!restoreCandidate) return;
	localText = restoreCandidate.text;
	activeTab = "letter";
	restoreCandidate = null;
}

async function handleOpenChange(open: boolean) {
	if (open) return;
	if (isDirty && isEditable) {
		await handleSave();
	}
	letterReview.close();
}
</script>

<Sheet.Root
    open={letterReview.vacancyId !== null}
    onOpenChange={handleOpenChange}
>
    <Sheet.Content
        side="right"
        class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl"
    >
        <Sheet.Header class="border-b border-border px-6 py-4">
            <Sheet.Title class="truncate pr-8 text-base">
                {vacancy?.title ?? `#${letterReview.vacancyId ?? ""}`}
            </Sheet.Title>
            <Sheet.Description class="truncate text-sm text-muted-foreground">
                {#if vacancy}
                    {vacancy.company_name ?? ""}{#if vacancy.salary}
                        · {vacancy.salary}
                    {/if}{#if vacancy.work_location}
                        · {vacancy.work_location}
                    {/if}
                {:else}
                    &nbsp;
                {/if}
            </Sheet.Description>
        </Sheet.Header>

        <Tabs.Root
            value={activeTab}
            onValueChange={(v) => (activeTab = v as "letter" | "history")}
            class="flex min-h-0 flex-1 flex-col gap-0"
        >
            <Tabs.List class="mx-6 mt-3 w-fit shrink-0">
                <Tabs.Trigger value="letter">
                    {m.review_tab_letter()}
                </Tabs.Trigger>
                <Tabs.Trigger value="history">
                    {m.review_tab_history()}
                    {#if coverLettersHistory.data && coverLettersHistory.data.length > 0}
                        <Badge variant="secondary" class="ml-1.5 h-4 px-1 text-[10px]">
                            {coverLettersHistory.data.length}
                        </Badge>
                    {/if}
                </Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content
                value="letter"
                class="m-0 min-h-0 flex-1 overflow-y-auto"
            >
                {#if isLoading}
                    <div class="space-y-3 p-6">
                        <Skeleton class="h-4 w-32 rounded" />
                        <Skeleton class="h-64 w-full rounded-md" />
                    </div>
                {:else if isErrorState}
                    <div class="p-6">
                        <p class="text-sm text-destructive">
                            {m.review_load_error({
                                error:
                                    errMsg(applicationStatus.error) ||
                                    errMsg(latestCoverLetter.error),
                            })}
                        </p>
                    </div>
                {:else if status === "parsed" || !hasApplication}
                    <div
                        class="flex flex-col items-center justify-center gap-2 p-12 text-center"
                    >
                        <p class="text-sm font-medium">
                            {m.review_empty_letter_title()}
                        </p>
                        <p class="text-sm text-muted-foreground">
                            {m.review_empty_letter_hint()}
                        </p>
                    </div>
                {:else if status === "letter_pending" || isGenerating}
                    <div
                        class="flex flex-col items-center justify-center gap-2 p-12 text-center"
                    >
                        <div
                            class="size-6 animate-spin rounded-full border-2 border-muted border-t-foreground"
                        ></div>
                        <p class="text-sm font-medium">
                            {m.review_generating_title()}
                        </p>
                        <p class="text-sm text-muted-foreground">
                            {m.review_generating_hint()}
                        </p>
                    </div>
                {:else}
                    <div class="space-y-3 p-6">
                        {#if status === "letter_sending"}
                            <p
                                class="flex items-center gap-2 text-sm text-muted-foreground"
                            >
                                <span
                                    class="size-2 animate-pulse rounded-full bg-amber-500"
                                ></span>
                                {m.review_sending_status()}
                            </p>
                        {:else if status === "letter_sent"}
                            <Badge variant="default">
                                {m.review_sent_status()}
                            </Badge>
                        {:else if status === "skipped"}
                            <Badge variant="ghost">
                                {m.review_skipped_status()}
                            </Badge>
                        {:else if status === "error" && applicationStatus.data?.reason}
                            <div
                                class="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                            >
                                {applicationStatus.data.reason}
                            </div>
                        {/if}

                        <Textarea
                            bind:value={localText}
                            readonly={isReadOnlyText}
                            rows={14}
                            placeholder={m.review_textarea_placeholder()}
                            class={isReadOnlyText ? "opacity-70" : ""}
                        />

                        <p class="text-xs text-muted-foreground">
                            {#if isDirty && isEditable}
                                {m.review_dirty_hint()}
                            {:else if latestCoverLetter.data}
                                {m.review_clean_hint({
                                    version: latestCoverLetter.data.version,
                                })}
                            {/if}
                        </p>
                    </div>
                {/if}
            </Tabs.Content>

            <Tabs.Content
                value="history"
                class="m-0 min-h-0 flex-1 overflow-hidden"
            >
                {#if coverLettersHistory.isPending}
                    <div class="space-y-2 p-6">
                        <Skeleton class="h-16 w-full rounded-md" />
                        <Skeleton class="h-16 w-full rounded-md" />
                    </div>
                {:else if coverLettersHistory.isError}
                    <p class="p-6 text-sm text-destructive">
                        {m.review_load_error({
                            error: errMsg(coverLettersHistory.error),
                        })}
                    </p>
                {:else if !coverLettersHistory.data || coverLettersHistory.data.length === 0}
                    <p class="p-6 text-sm text-muted-foreground">
                        {m.review_history_empty()}
                    </p>
                {:else}
                    <ScrollArea class="h-full">
                        <ul class="space-y-3 p-6">
                            {#each coverLettersHistory.data as version (version.version)}
                                <li
                                    class="space-y-2 rounded-md border border-border p-3"
                                >
                                    <div
                                        class="flex items-start justify-between gap-2"
                                    >
                                        <div class="flex items-center gap-2">
                                            <Badge variant="outline">
                                                {m.review_history_version_label(
                                                    { version: version.version },
                                                )}
                                            </Badge>
                                            <span
                                                class="text-xs text-muted-foreground"
                                            >
                                                {new Date(
                                                    version.created_at,
                                                ).toLocaleString()}
                                            </span>
                                        </div>
                                        {#if isEditable}
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onclick={() =>
                                                    startRestore(version)}
                                            >
                                                {m.review_button_restore()}
                                            </Button>
                                        {/if}
                                    </div>
                                    <p
                                        class="line-clamp-3 whitespace-pre-wrap text-sm text-muted-foreground"
                                    >
                                        {version.text}
                                    </p>
                                </li>
                            {/each}
                        </ul>
                    </ScrollArea>
                {/if}
            </Tabs.Content>
        </Tabs.Root>

        <Sheet.Footer
            class="flex-row items-center justify-between gap-2 border-t border-border px-6 py-3"
        >
            {#if status === "parsed" || !hasApplication}
                <div></div>
                <Button onclick={handleGenerate} disabled={isGenerating}>
                    {m.review_button_generate()}
                </Button>
            {:else if status === "letter_pending"}
                <div></div>
                <Button disabled>{m.review_button_generate()}</Button>
            {:else if status === "letter_ready" || status === "letter_reviewing"}
                <Button
                    variant="ghost"
                    onclick={handleSkip}
                    disabled={isSkipping}
                >
                    {m.review_button_skip()}
                </Button>
                <div class="flex gap-2">
                    <Button
                        variant="outline"
                        onclick={handleGenerate}
                        disabled={isGenerating}
                    >
                        {m.review_button_regenerate()}
                    </Button>
                    <Button
                        variant="outline"
                        onclick={handleSave}
                        disabled={isSaving || !isDirty}
                    >
                        {isSaving
                            ? m.review_button_saving()
                            : m.review_button_save()}
                    </Button>
                    <Button onclick={handleSubmit} disabled={isSubmitting}>
                        {isSubmitting
                            ? m.review_button_submitting()
                            : m.review_button_submit()}
                    </Button>
                </div>
            {:else if status === "error"}
                <Button
                    variant="ghost"
                    onclick={handleSkip}
                    disabled={isSkipping}
                >
                    {m.review_button_skip()}
                </Button>
                <Button onclick={handleRetry} disabled={isRetrying}>
                    {m.review_button_retry()}
                </Button>
            {:else}
                <div></div>
                <Button
                    variant="ghost"
                    onclick={() => letterReview.close()}
                >
                    {m.review_button_close()}
                </Button>
            {/if}
        </Sheet.Footer>
    </Sheet.Content>
</Sheet.Root>

<AlertDialog.Root
    open={restoreCandidate !== null}
    onOpenChange={(o) => {
        if (!o) restoreCandidate = null;
    }}
>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>
                {m.review_restore_title({
                    version: restoreCandidate?.version ?? 0,
                })}
            </AlertDialog.Title>
            <AlertDialog.Description>
                {m.review_restore_description()}
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>
                {m.review_restore_cancel()}
            </AlertDialog.Cancel>
            <AlertDialog.Action onclick={confirmRestore}>
                {m.review_restore_confirm()}
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>
