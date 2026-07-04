export const Utils = {
	numeric: {
		parseOptional: (raw: string | number): number => {
			if (typeof raw === "number") {
				return raw;
			}
			const trimmed = raw.trim();
			if (trimmed === "") return 0;
			const n = Number(trimmed);
			return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
		},
	},
};
