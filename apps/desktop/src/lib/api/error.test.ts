import { describe, expect, it } from "vitest";
import { APIError } from "./error";

describe("APIError", () => {
	it("carries status + detail through the Error contract", () => {
		const err = new APIError(404, "Vacancy not found");
		expect(err).toBeInstanceOf(Error);
		expect(err).toBeInstanceOf(APIError);
		expect(err.status).toBe(404);
		expect(err.detail).toBe("Vacancy not found");
		expect(err.message).toBe("Vacancy not found");
	});

	it("is catchable via instanceof", () => {
		const throwing = () => {
			throw new APIError(500, "boom");
		};
		try {
			throwing();
			expect.unreachable();
		} catch (e) {
			expect(e instanceof APIError).toBe(true);
			expect((e as APIError).status).toBe(500);
		}
	});
});
