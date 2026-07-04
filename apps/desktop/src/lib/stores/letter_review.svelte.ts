export class LetterReviewStore {
	vacancyId = $state<number | null>(null);

	open(id: number) {
		this.vacancyId = id;
	}

	close() {
		this.vacancyId = null;
	}
}

export const letterReview = new LetterReviewStore();
