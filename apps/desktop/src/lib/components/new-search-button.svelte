<script lang="ts">
import { BOARDS, BOARD_ORDER, type BoardKind } from "$lib/boards";
import { Badge } from "$lib/components/ui/badge";
import { buttonVariants } from "$lib/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "$lib/components/ui/dropdown-menu";
import { m } from "$lib/paraglide/messages";
import ChevronDown from "@lucide/svelte/icons/chevron-down";

const {
	disabled = false,
	onSelect,
}: {
	disabled?: boolean;
	onSelect: (kind: BoardKind) => void;
} = $props();
</script>

<DropdownMenu>
	<DropdownMenuTrigger class={buttonVariants()} {disabled}>
		{m.queue_button_new_search()}
		<ChevronDown class="size-4" />
	</DropdownMenuTrigger>
	<DropdownMenuContent align="end" class="min-w-52">
		{#each BOARD_ORDER as kind (kind)}
			{@const board = BOARDS[kind]}
			{@const BoardIcon = board.icon}
			<DropdownMenuItem
				disabled={!board.enabled}
				onSelect={() => onSelect(kind)}
			>
				<BoardIcon class="size-4" />
				<span class="flex-1">{board.label()}</span>
				{#if !board.enabled}
					<Badge variant="secondary">{m.board_badge_coming_soon()}</Badge>
				{/if}
			</DropdownMenuItem>
		{/each}
	</DropdownMenuContent>
</DropdownMenu>
