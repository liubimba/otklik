import { BOARDS, type BoardKind } from "$lib/boards";

const STORAGE_KEY = "otklik.active-board";

function isBoardKind(value: string | null): value is BoardKind {
	return value !== null && value in BOARDS;
}

function load(): BoardKind {
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (isBoardKind(stored)) return stored;
	} catch {}
	return "hh_ru";
}

function persist(board: BoardKind): void {
	try {
		localStorage.setItem(STORAGE_KEY, board);
	} catch {}
}

function createBoardStore() {
	let active = $state<BoardKind>(load());

	return {
		get active(): BoardKind {
			return active;
		},
		set(board: BoardKind): void {
			active = board;
			persist(board);
		},
	};
}

export const boardStore = createBoardStore();
