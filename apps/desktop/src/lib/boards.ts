import { m } from "$lib/paraglide/messages";
import Briefcase from "@lucide/svelte/icons/briefcase";
import Newspaper from "@lucide/svelte/icons/newspaper";

export type BoardKind = "hh_ru" | "habr";

export type BoardMeta = {
	label: () => string;
	icon: typeof Briefcase;
	enabled: boolean;
};

export const BOARDS: Record<BoardKind, BoardMeta> = {
	hh_ru: { label: m.queue_board_hh_ru, icon: Briefcase, enabled: true },
	habr: { label: m.queue_board_habr, icon: Newspaper, enabled: false },
};

export const BOARD_ORDER: readonly BoardKind[] = ["hh_ru", "habr"];
