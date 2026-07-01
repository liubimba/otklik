<script lang="ts">
    import * as AlertDialog from "$lib/components/ui/alert-dialog";
    import {Badge} from "$lib/components/ui/badge";
    import {Button} from "$lib/components/ui/button";
    import {ScrollArea} from "$lib/components/ui/scroll-area";
    import * as Sheet from "$lib/components/ui/sheet";
    import {Skeleton} from "$lib/components/ui/skeleton";
    import * as Tabs from "$lib/components/ui/tabs";
    import {Textarea} from "$lib/components/ui/textarea";
    import {m} from "$lib/paraglide/messages";
    import {
        createApplicationQuery,
        createCoverLettersHistoryQuery,
    } from "$lib/queries/applications";
    import {useQueryClient} from "@tanstack/svelte-query";
    import {createActions} from "$lib/actions";
    import {store} from "$lib/stores";
    import {lifecycle} from "$lib/model";
    import type {Tab} from "$lib/model/letter-review-sheet.viewmodel.svelte";

    const queryClient = useQueryClient();
    const actions = createActions(queryClient);

    const applicationStatus = createApplicationQuery(
        () => store.letter.review.vacancyId,
    );
    const coverLettersHistory = createCoverLettersHistoryQuery(
        () => store.letter.review.vacancyId,
    );

    const model = lifecycle.letter.review.viewmodel(
        queryClient,
        store.letter.review,
        applicationStatus,
        coverLettersHistory,
    );
    const view = lifecycle.letter.review.view(actions, store.letter.review, model);

    // Sync the editor buffer from the ApplicationDetail.latest_letter that
    // the server returns on GET /vacancies/{id}/application (one hit instead
    // of a separate cover_letter fetch). Every server-driven sync resets
    // the undo history — Ctrl+Z must not cross a version boundary and
    // reveal a stale text the user did not type.
    $effect(() => {
        const id = store.letter.review.vacancyId;
        const latest = applicationStatus.data?.latest_letter ?? null;
        if (id === null) {
            model.cover_letter.setText("", { pushHistory: false });
            model.cover_letter.clearHistory();
            model.cover_letter.lastSyncedVersion = null;
            model.tab = "letter";
            return;
        }
        if (latest && latest.version !== model.cover_letter.lastSyncedVersion) {
            model.cover_letter.setText(latest.text, { pushHistory: false });
            model.cover_letter.clearHistory();
            model.cover_letter.lastSyncedVersion = latest.version;
        }
    });

    function handleTextareaKeydown(event: KeyboardEvent) {
        const isMod = event.ctrlKey || event.metaKey;
        if (!isMod) return;
        const key = event.key.toLowerCase();
        // Cmd/Ctrl+Shift+Z or Cmd/Ctrl+Y — redo.
        if ((key === "z" && event.shiftKey) || key === "y") {
            if (model.cover_letter.canRedo) {
                event.preventDefault();
                view.redo();
            }
            return;
        }
        // Cmd/Ctrl+Z — undo. The browser's built-in undo stack is wiped
        // on every programmatic value replacement (initial sync, restore
        // from history), so we keep our own and swallow the event.
        if (key === "z") {
            if (model.cover_letter.canUndo) {
                event.preventDefault();
                view.undo();
            }
        }
    }
</script>

<Sheet.Root
    open={model.isOpen}
    onOpenChange={(o) => {
        if (!o) view.close();
    }}
>
    <Sheet.Content
        side="right"
        class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl"
    >
        <Sheet.Header class="border-b border-border px-6 py-4">
            <Sheet.Title class="truncate pr-8 text-base">
                {model.review.vacancy?.title ??
                    `#${store.letter.review.vacancyId ?? ""}`}
            </Sheet.Title>
            <Sheet.Description class="truncate text-sm text-muted-foreground">
                {#if model.review.vacancy}
                    {model.review.vacancy.company_name ?? ""}{#if model.review.vacancy.salary}
                        · {model.review.vacancy.salary}
                    {/if}{#if model.review.vacancy.work_location}
                        · {model.review.vacancy.work_location}
                    {/if}
                {:else}
                    &nbsp;
                {/if}
            </Sheet.Description>
        </Sheet.Header>

        <Tabs.Root
            value={model.tab}
            onValueChange={(v) => view.setTab(v as Tab)}
            class="flex min-h-0 flex-1 flex-col gap-0"
        >
            <Tabs.List class="mx-6 mt-3 w-fit shrink-0">
                <Tabs.Trigger value="letter">
                    {m.review_tab_letter()}
                </Tabs.Trigger>
                <Tabs.Trigger value="history">
                    {m.review_tab_history()}
                    {#if model.coverLettersHistory.data && model.coverLettersHistory.data.length > 0}
                        <Badge
                            variant="secondary"
                            class="ml-1.5 h-4 px-1 text-[10px]"
                        >
                            {model.coverLettersHistory.data.length}
                        </Badge>
                    {/if}
                </Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content
                value="letter"
                class="m-0 min-h-0 flex-1 overflow-y-auto"
            >
                {#if model.review.isLoading}
                    <div class="space-y-3 p-6">
                        <Skeleton class="h-4 w-32 rounded" />
                        <Skeleton class="h-64 w-full rounded-md" />
                    </div>
                {:else if model.review.isError}
                    <div class="p-6">
                        <p class="text-sm text-destructive">
                            {m.review_load_error({
                                error:
                                    view.errMsg(model.applicationStatus.error),
                            })}
                        </p>
                    </div>
                {:else if model.review.status === "parsed" || !model.review.hasApplication}
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
                {:else if model.review.isGenerating}
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
                        {#if model.review.status === "error"}
                            <div
                                    class="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                            >
                                <span>{m.error()}: {model.review.error ? model.review.error : m.review_sent_unknown_error()}</span>
                            </div>
                        {/if}

                        {#if model.review.isSubmitting}
                            <p
                                class="flex items-center gap-2 text-sm text-muted-foreground"
                            >
                                <span
                                    class="size-2 animate-pulse rounded-full bg-amber-500"
                                ></span>
                                {m.review_sending_status()}
                            </p>
                        {:else if model.review.status === "letter_sent"}
                            <Badge variant="default">
                                {m.review_sent_status()}
                            </Badge>
                        {:else if model.review.status === "skipped"}
                            <Badge variant="ghost">
                                {m.review_skipped_status()}
                            </Badge>
                        {:else if model.review.status === "error" && model.applicationStatus.data?.reason}
                            <div
                                class="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                            >
                                {model.applicationStatus.data.reason}
                            </div>
                        {/if}

                        <Textarea
                            value={model.cover_letter.localText}
                            oninput={(e) =>
                                model.cover_letter.setText(
                                    (e.currentTarget as HTMLTextAreaElement).value,
                                )}
                            onkeydown={handleTextareaKeydown}
                            readonly={model.cover_letter.isReadOnly}
                            rows={14}
                            placeholder={m.review_textarea_placeholder()}
                            class={model.cover_letter.isReadOnly ? "opacity-70" : ""}
                        />

                        <p class="text-xs text-muted-foreground">
                            {#if model.cover_letter.isDirty && model.cover_letter.isEditable}
                                {m.review_dirty_hint()}
                            {:else if model.cover_letter.latest}
                                {m.review_clean_hint({
                                    version: model.cover_letter.latest.version,
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
                {#if model.coverLettersHistory.isPending}
                    <div class="space-y-2 p-6">
                        <Skeleton class="h-16 w-full rounded-md" />
                        <Skeleton class="h-16 w-full rounded-md" />
                    </div>
                {:else if model.coverLettersHistory.isError}
                    <p class="p-6 text-sm text-destructive">
                        {m.review_load_error({
                            error: view.errMsg(model.coverLettersHistory.error),
                        })}
                    </p>
                {:else if !model.coverLettersHistory.data || model.coverLettersHistory.data.length === 0}
                    <p class="p-6 text-sm text-muted-foreground">
                        {m.review_history_empty()}
                    </p>
                {:else}
                    <ScrollArea class="h-full">
                        <ul class="space-y-3 p-6">
                            {#each model.coverLettersHistory.data as version (version.version)}
                                <li
                                    class="space-y-2 rounded-md border border-border p-3"
                                >
                                    <div
                                        class="flex items-start justify-between gap-2"
                                    >
                                        <div class="flex items-center gap-2">
                                            <Badge variant="outline">
                                                {m.review_history_version_label(
                                                    {version: version.version},
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
                                        {#if model.cover_letter.isEditable}
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onclick={() =>
                                                    view.startRestore(version)}
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
            {#if model.review.status === "parsed" || !model.review.hasApplication}
                <div></div>
                <Button
                    onclick={view.generate}
                    disabled={model.review.isGenerating}
                >
                    {m.review_button_generate()}
                </Button>
            {:else if model.review.isGenerating}
                <div></div>
                <Button disabled>{m.review_button_generate()}</Button>
            {:else if model.review.status === "letter_ready" || model.review.status === "letter_reviewing"}
                <Button variant="ghost" onclick={view.skip}>
                    {m.review_button_skip()}
                </Button>
                <div class="flex gap-2">
                    <Button
                        variant="outline"
                        onclick={view.generate}
                        disabled={model.review.isGenerating}
                    >
                        {m.review_button_regenerate()}
                    </Button>
                    {#if model.cover_letter.showSaveButton}
                        <Button
                            variant="outline"
                            onclick={view.save}
                            disabled={!model.cover_letter.isDirty}
                        >
                            {m.review_button_save()}
                        </Button>
                    {/if}
                    <Button
                        onclick={view.submit}
                        disabled={model.review.isSubmitting}
                    >
                        {model.review.isSubmitting
                            ? m.review_button_submitting()
                            : m.review_button_submit()}
                    </Button>
                </div>
            {:else if model.review.status === "error"}
                <Button variant="ghost" onclick={view.skip}>
                    {m.review_button_skip()}
                </Button>
                <div class="flex gap-2">
                    {#if model.cover_letter.showSaveButton}
                        <Button
                            variant="outline"
                            onclick={view.save}
                            disabled={!model.cover_letter.isDirty}
                        >
                            {m.review_button_save()}
                        </Button>
                    {/if}
                    <Button onclick={view.retry}>
                        {m.review_button_retry()}
                    </Button>
                </div>
            {:else}
                <div></div>
                <Button variant="ghost" onclick={view.close}>
                    {m.review_button_close()}
                </Button>
            {/if}
        </Sheet.Footer>
    </Sheet.Content>
</Sheet.Root>

<AlertDialog.Root
    open={model.cover_letter.restoreCandidate !== null}
    onOpenChange={(o) => {
        if (!o) view.cancelRestore();
    }}
>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>
                {m.review_restore_title({
                    version: model.cover_letter.restoreCandidate?.version ?? 0,
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
            <AlertDialog.Action onclick={view.confirmRestore}>
                {m.review_restore_confirm()}
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>
