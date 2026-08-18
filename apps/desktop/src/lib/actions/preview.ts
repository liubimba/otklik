import { API } from "$lib/api/client";
import type { PreviewCoverLetterRequest } from "$lib/api/types";
import { type QueryClient, createMutation } from "@tanstack/svelte-query";

export function createPreviewActions(_queryClient: QueryClient) {
	return {
		generate: createMutation(() => ({
			mutationFn: (body: PreviewCoverLetterRequest) =>
				API.ai.previewCoverLetter(body),
		})),
	};
}
