<script lang="ts">
import { createActions } from "$lib/actions";
import * as AlertDialog from "$lib/components/ui/alert-dialog";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import { ScrollArea } from "$lib/components/ui/scroll-area";
import * as Sheet from "$lib/components/ui/sheet";
import { Skeleton } from "$lib/components/ui/skeleton";
import * as Tabs from "$lib/components/ui/tabs";
import { Textarea } from "$lib/components/ui/textarea";
import { lifecycle } from "$lib/model";
import type { Tab } from "$lib/model/letter-review-sheet.viewmodel.svelte";
import { m } from "$lib/paraglide/messages";
import {
	createApplicationQuery,
	createCoverLettersHistoryQuery,
} from "$lib/queries/applications";
import { store } from "$lib/stores";
import RefreshCw from "@lucide/svelte/icons/refresh-cw";
import Save from "@lucide/svelte/icons/save";
import { useQueryClient } from "@tanstack/svelte-query";
import {
	SHEET_WIDTH_DEFAULT,
	clampSheetWidth,
	persistSheetWidth,
	readPersistedSheetWidth,
} from "./letter-review-sheet.width";

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

// Drag-to-resize state. Width is loaded from localStorage on mount
// (falling back to SHEET_WIDTH_DEFAULT) and persisted on every commit.
// Viewport width is tracked reactively so the sheet re-clamps when
// the Tauri window itself is resized — otherwise a saved 900px sheet
// would keep its width even when the user shrinks the window to
// 600px and hide the app behind it.
let width = $state(SHEET_WIDTH_DEFAULT);
let viewportWidth = $state(SHEET_WIDTH_DEFAULT * 2);
let isDragging = $state(false);

$effect(() => {
	viewportWidth = window.innerWidth;
	width = readPersistedSheetWidth(window.innerWidth);
	const onResize = () => {
		viewportWidth = window.innerWidth;
		width = clampSheetWidth(width, window.innerWidth);
	};
	window.addEventListener("resize", onResize);
	return () => window.removeEventListener("resize", onResize);
});

function onResizePointerDown(event: PointerEvent) {
	// Only capture primary button drags — right-click, middle-click,
	// and touch-scroll gestures must not resize the sheet.
	if (event.button !== 0) return;
	event.preventDefault();
	const target = event.currentTarget as HTMLElement;
	target.setPointerCapture(event.pointerId);
	const startX = event.clientX;
	const startWidth = width;
	isDragging = true;

	function onMove(moveEvent: PointerEvent) {
		// Sheet lives on the right edge, so a leftward drag (clientX
		// decreasing) grows the width, and rightward shrinks it.
		const delta = startX - moveEvent.clientX;
		width = clampSheetWidth(startWidth + delta, window.innerWidth);
	}

	function onUp(upEvent: PointerEvent) {
		target.releasePointerCapture(upEvent.pointerId);
		target.removeEventListener("pointermove", onMove);
		target.removeEventListener("pointerup", onUp);
		target.removeEventListener("pointercancel", onUp);
		isDragging = false;
		// Persist ONCE per drag, on release. A prior `$effect(() =>
		// persistSheetWidth(width))` fired on every pointermove
		// (~60 Hz) — a synchronous localStorage.setItem per frame
		// dropped drag FPS well below the display refresh rate.
		persistSheetWidth(width);
	}

	target.addEventListener("pointermove", onMove);
	target.addEventListener("pointerup", onUp);
	target.addEventListener("pointercancel", onUp);
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
        class="flex flex-col gap-0 p-0"
        style="width: {width}px; max-width: {viewportWidth}px;"
    >
        <!--
            Drag-to-resize handle on the left edge. Absolutely positioned
            so it doesn't disturb the flex layout of the sheet body.
            4px wide (comfortable pointer target) with a slight visual
            hint on hover / active drag. Uses pointer events (not mouse)
            so pen / touch also work, and Pointer Capture so the drag
            keeps updating even when the cursor leaves the strip.
        -->
        <div
            class="absolute inset-y-0 left-0 z-50 w-1 cursor-ew-resize transition-colors hover:bg-border {isDragging
                ? 'bg-border'
                : ''}"
            role="separator"
            aria-orientation="vertical"
            aria-label="Изменить ширину"
            onpointerdown={onResizePointerDown}
        ></div>
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
                        {/if}

                        {#if model.review.status === "error"}
                            <!--
                                Single error banner rendered right above the
                                textarea. Prior to 2026-07-01 the template
                                duplicated this: one banner at the top of the
                                content block, one after the status area.
                            -->
                            <div
                                class="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                            >
                                {m.error()}: {model.review.error ??
                                    m.review_sent_unknown_error()}
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

                        <!--
                            Textarea toolbar: dirty/clean hint on the left,
                            letter meta-actions (Regenerate, Save) as icon
                            buttons on the right. Kept adjacent to the
                            textarea on purpose — they act on the letter
                            content, unlike the footer's Skip / Submit which
                            act on the application flow.
                        -->
                        <div
                            class="flex min-h-7 items-center justify-between gap-2"
                        >
                            <p class="text-xs text-muted-foreground">
                                {#if model.cover_letter.isDirty && model.cover_letter.isEditable}
                                    {m.review_dirty_hint()}
                                {:else if model.cover_letter.latest}
                                    {m.review_clean_hint({
                                        version: model.cover_letter.latest.version,
                                    })}
                                {/if}
                            </p>
                            <div class="flex items-center gap-1">
                                {#if model.review.canRegenerate}
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        onclick={view.generate}
                                        disabled={model.review.isGenerating}
                                        aria-label={m.review_button_regenerate()}
                                    >
                                        <RefreshCw />
                                    </Button>
                                {/if}
                                {#if model.cover_letter.showSaveButton}
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        onclick={view.save}
                                        disabled={!model.cover_letter.isDirty}
                                        aria-label={m.review_button_save()}
                                    >
                                        <Save />
                                    </Button>
                                {/if}
                            </div>
                        </div>
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
            {:else if model.review.status === "letter_ready" || model.review.status === "letter_reviewing" || model.review.status === "error"}
                <!--
                    Footer carries only application-flow actions: Skip
                    (destructive-terminal, ghost, left) and Submit (primary
                    CTA, filled, right). Letter meta-actions (Regenerate,
                    Save) live in the textarea toolbar above — same status
                    ladder, but associated with the letter content rather
                    than with the sheet's flow. ERROR ends up here on
                    purpose: the ERROR → LETTER_SENDING arc lets the user
                    retry Submit without first going through RETRY.
                -->
                <Button variant="ghost" onclick={view.skip}>
                    {m.review_button_skip()}
                </Button>
                <Button
                    onclick={view.submit}
                    disabled={model.review.isSubmitting}
                >
                    {model.review.isSubmitting
                        ? m.review_button_submitting()
                        : m.review_button_submit()}
                </Button>
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
