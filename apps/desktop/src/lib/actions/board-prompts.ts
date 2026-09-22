import { API } from "$lib/api/client";
import type { BoardPrompt, BoardPrompts } from "$lib/api/types";
import type { BoardKind } from "$lib/boards";
import { boardPromptsQueryKey } from "$lib/queries/board_prompts";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createBoardPromptsActions(queryClient: QueryClient) {
	return {
		save: createMutation(() => ({
			mutationFn: (params: { board: BoardKind; prompt: BoardPrompt }) =>
				API.boardPrompts.set(params.board, params.prompt),
			onSuccess(saved: BoardPrompts) {
				queryClient.setQueryData(boardPromptsQueryKey, saved);
			},
		})),
	};
}
