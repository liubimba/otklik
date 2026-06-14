export class APIError extends Error {
	constructor(
		public status: number,
		public detail: string,
	) {
		super(detail);
	}
}
