import { createLetterReviewSheetView } from "$lib/model/letter-review-sheet.view.svelte";
import { createLetterReviewSheetViewModel } from "$lib/model/letter-review-sheet.viewmodel.svelte";

export const lifecycle = {
	letter: {
		review: {
			view: createLetterReviewSheetView,
			viewmodel: createLetterReviewSheetViewModel,
		},
	},
};
