import { letterReview } from "$lib/stores/letter_review.svelte";
import { searchFilterStateStore } from "$lib/stores/search_filter.store.svelte";

export const store = {
	search: {
		filter: searchFilterStateStore,
	},
	letter: {
		review: letterReview,
	},
};
