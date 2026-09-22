<script lang="ts">
import type { BoardPrompt, BoardPromptMode } from "$lib/api/types";
import { BOARDS, type BoardKind } from "$lib/boards";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import { Textarea } from "$lib/components/ui/textarea";
import { m } from "$lib/paraglide/messages";
import ChevronDown from "@lucide/svelte/icons/chevron-down";
import Sparkles from "@lucide/svelte/icons/sparkles";

const {
	active,
	value,
	pending,
	onSave,
}: {
	active: BoardKind;
	value: BoardPrompt | undefined;
	pending: boolean;
	onSave: (prompt: BoardPrompt) => void;
} = $props();

// biome-ignore lint/style/useConst: reassigned from the header toggle in the template
let expanded = $state(false);
let mode = $state<BoardPromptMode>("append");
let text = $state("");
let seededMode = $state<BoardPromptMode>("append");
let seededText = $state("");
let seededBoard = $state<BoardKind | null>(null);

const savedMode = $derived<BoardPromptMode>(value?.mode ?? "append");
const savedText = $derived(value?.text ?? "");

$effect(() => {
	const boardChanged = seededBoard !== active;
	const untouched = mode === seededMode && text === seededText;
	if (boardChanged || untouched) {
		mode = savedMode;
		text = savedText;
		seededMode = savedMode;
		seededText = savedText;
		seededBoard = active;
	}
});

const trimmed = $derived(text.trim());
const isSet = $derived(savedText !== "");
const dirty = $derived(
	trimmed !== savedText || (trimmed !== "" && mode !== savedMode),
);

function save() {
	onSave({ mode, text: trimmed });
}
</script>

<section class="bg-card overflow-hidden rounded-lg border text-sm">
	<button
		type="button"
		onclick={() => (expanded = !expanded)}
		aria-expanded={expanded}
		class="flex w-full cursor-pointer items-center gap-2.5 px-4 py-3 text-left transition-colors hover:bg-muted/40"
	>
		<Sparkles class="text-muted-foreground size-4 shrink-0" />
		<span class="font-medium">{m.queue_board_prompt_title()}</span>
		<span class="text-muted-foreground">· {BOARDS[active].label()}</span>
		{#if isSet}
			<Badge variant="secondary" class="ml-0.5">
				{m.queue_board_prompt_active_badge()}
			</Badge>
		{/if}
		<ChevronDown
			class="text-muted-foreground ml-auto size-4 shrink-0 transition-transform duration-200 {expanded
				? 'rotate-180'
				: ''}"
		/>
	</button>

	{#if expanded}
		<div class="space-y-3 border-t px-4 py-3">
			<div
				class="bg-muted/50 inline-flex items-center gap-1 rounded-lg border p-1"
				role="radiogroup"
				aria-label={m.queue_board_prompt_title()}
			>
				{#each [{ id: "append", label: m.queue_board_prompt_mode_append }, { id: "replace", label: m.queue_board_prompt_mode_replace }] as option (option.id)}
					{@const selected = mode === option.id}
					<button
						type="button"
						role="radio"
						aria-checked={selected}
						onclick={() => (mode = option.id as BoardPromptMode)}
						class="cursor-pointer rounded-md px-3 py-1 text-sm font-medium transition-colors {selected
							? 'bg-background text-foreground shadow-sm'
							: 'text-muted-foreground hover:text-foreground'}"
					>
						{option.label()}
					</button>
				{/each}
			</div>

			<Textarea
				bind:value={text}
				rows={6}
				placeholder={m.queue_board_prompt_placeholder()}
				class="resize-y font-mono text-xs leading-relaxed"
			/>

			<div class="flex items-center justify-between gap-3">
				<p class="text-muted-foreground text-xs">
					{mode === "replace"
						? m.queue_board_prompt_hint_replace()
						: m.queue_board_prompt_hint_append()}
				</p>
				<Button size="sm" onclick={save} disabled={!dirty || pending}>
					{pending
						? m.queue_board_prompt_saving()
						: m.queue_board_prompt_save()}
				</Button>
			</div>
		</div>
	{/if}
</section>
