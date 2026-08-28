import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const config = readFileSync(
	resolve(process.cwd(), "electron-builder.yml"),
	"utf8",
);

describe("electron-builder deb packaging", () => {
	it("declares Replaces on the former package name so dpkg -i can take over /opt/Otklik from a 0.6.0 install", () => {
		expect(config).toMatch(/replaces/i);
		expect(config).toMatch(/replaces[\s=:"'-]*\n?\s*[-"']*\s*desktop/i);
	});

	it("does not declare Conflicts/Breaks on desktop, which would block the updater's dpkg -i", () => {
		expect(config).not.toMatch(/conflicts[\s=:"'-]*\n?\s*[-"']*\s*desktop/i);
		expect(config).not.toMatch(/breaks[\s=:"'-]*\n?\s*[-"']*\s*desktop/i);
	});
});
