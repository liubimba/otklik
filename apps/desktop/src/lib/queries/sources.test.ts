import { describe, expect, it } from "vitest";
import { query } from "./index";
import { createSourcesQuery, sourcesQueryKey } from "./sources";

describe("sourcesQueryKey", () => {
	it("is a stable context-sources key", () => {
		expect(sourcesQueryKey).toEqual(["context-sources"]);
	});
});

describe("query.sources", () => {
	it("registers the key and create function", () => {
		expect(query.sources.key).toBe(sourcesQueryKey);
		expect(query.sources.create).toBe(createSourcesQuery);
	});
});
