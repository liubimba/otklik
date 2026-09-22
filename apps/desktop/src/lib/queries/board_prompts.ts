import { API } from "$lib/api/client";
import type { BoardPrompts } from "$lib/api/types";
import { createQuery } from "@tanstack/svelte-query";

export const boardPromptsQueryKey = ["board-prompts"] as const;

export function createBoardPromptsQuery() {
	return createQuery<BoardPrompts>(() => ({
		queryKey: boardPromptsQueryKey,
		queryFn: API.boardPrompts.get,
		staleTime: Number.POSITIVE_INFINITY,
	}));
}
