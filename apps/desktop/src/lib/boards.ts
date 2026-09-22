import { m } from "$lib/paraglide/messages";
import Briefcase from "@lucide/svelte/icons/briefcase";
import Newspaper from "@lucide/svelte/icons/newspaper";
import Store from "@lucide/svelte/icons/store";

export type BoardKind = "hh_ru" | "habr" | "kwork";

export type BoardMeta = {
	label: () => string;
	icon: typeof Briefcase;
	enabled: boolean;
};

export const BOARDS: Record<BoardKind, BoardMeta> = {
	hh_ru: { label: m.queue_board_hh_ru, icon: Briefcase, enabled: true },
	habr: { label: m.queue_board_habr, icon: Newspaper, enabled: true },
	kwork: { label: m.queue_board_kwork, icon: Store, enabled: true },
};

export const BOARD_ORDER: readonly BoardKind[] = ["hh_ru", "habr", "kwork"];
