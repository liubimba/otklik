<script lang="ts">
import { createSortable } from "@dnd-kit/svelte/sortable";
import type { Snippet } from "svelte";

interface Props {
	id: string;
	index: number;
	children: Snippet<
		[
			{
				attachHandle: (node: HTMLElement) => () => void;
				isDragging: boolean;
			},
		]
	>;
}

const { id, index, children }: Props = $props();

const sortable = createSortable({
	id,
	index,
	type: "llm-deployment",
});
</script>

<div
	{@attach sortable.attach}
	class="transition-opacity"
	class:opacity-50={sortable.isDragging}
>
	{@render children({
		attachHandle: sortable.attachHandle,
		isDragging: sortable.isDragging,
	})}
</div>
