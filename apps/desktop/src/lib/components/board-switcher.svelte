<script lang="ts">
import { BOARDS, BOARD_ORDER, type BoardKind } from "$lib/boards";
import { Badge } from "$lib/components/ui/badge";
import { m } from "$lib/paraglide/messages";

const {
	active,
	onSelect,
}: {
	active: BoardKind;
	onSelect: (board: BoardKind) => void;
} = $props();
</script>

<div
	class="bg-muted/50 inline-flex items-center gap-1 rounded-lg border p-1"
	role="tablist"
	aria-label={m.board_switcher_label()}
>
	{#each BOARD_ORDER as kind (kind)}
		{@const board = BOARDS[kind]}
		{@const BoardIcon = board.icon}
		{@const isActive = active === kind}
		<button
			type="button"
			role="tab"
			aria-selected={isActive}
			onclick={() => onSelect(kind)}
			class="flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors {isActive
				? 'bg-background text-foreground shadow-sm'
				: 'text-muted-foreground hover:text-foreground'}"
		>
			<BoardIcon class="size-4" />
			{board.label()}
			{#if !board.enabled}
				<Badge variant="secondary" class="ml-0.5">
					{m.board_badge_coming_soon()}
				</Badge>
			{/if}
		</button>
	{/each}
</div>
