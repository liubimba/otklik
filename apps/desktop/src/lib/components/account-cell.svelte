<script lang="ts">
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "$lib/components/ui/dropdown-menu";
import * as m from "$lib/paraglide/messages";
import ChevronsUpDown from "@lucide/svelte/icons/chevrons-up-down";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
import User from "@lucide/svelte/icons/user";
import WifiOff from "@lucide/svelte/icons/wifi-off";

export type AuthStatus =
	| "loading"
	| "unauthorized"
	| "authorizing"
	| "authorized"
	| "offline";

const {
	status,
	onSignIn,
	onSignOut,
	onCancel,
}: {
	status: AuthStatus;
	onSignIn: () => void;
	onSignOut: () => void;
	onCancel: () => void;
} = $props();

// Статус словами — вся суть переделки. Старая кнопка показывала иконку и
// шеврон и не сообщала ни площадку, ни состояние.
const statusLabel = $derived(
	{
		loading: "",
		unauthorized: m.account_status_unauthorized(),
		authorizing: m.account_status_authorizing(),
		authorized: m.account_status_authorized(),
		offline: m.account_status_offline(),
	}[status],
);

// `unauthorized`/`authorizing` still act on a single click — both are safe
// and reversible (sign-in just opens hh.ru's own login flow; cancel aborts
// it). `authorized` is deliberately NOT handled here: signing out drops the
// persistent browser session and forces the whole re-auth flow, so it must
// go through an explicit menu item («Выйти»), never a bare click on the
// cell. See the DropdownMenu branch below.
function activate() {
	if (status === "unauthorized") onSignIn();
	else if (status === "authorizing") onCancel();
}

// The accessible name must say what activation does — "hh.ru, Подключён"
// tells a screen-reader user nothing about the fact that clicking used to
// sign them out. Each state gets a label naming its actual effect.
const ariaLabel = $derived(
	{
		loading: "",
		unauthorized: m.account_aria_sign_in(),
		authorizing: m.account_aria_cancel(),
		authorized: m.account_aria_open_menu(),
		offline: "",
	}[status],
);
</script>

{#snippet avatar()}
	<span
		class="relative flex size-7 shrink-0 items-center justify-center rounded-full border bg-muted"
	>
		{#if status === "authorizing"}
			<LoaderCircle class="size-[15px] animate-spin text-muted-foreground" />
		{:else}
			<User class="size-[15px] text-muted-foreground" />
			<!--
				Точка статуса монохромная: в палитре нет зелёного, и заводить
				его ради одного индикатора нельзя.
			-->
			<span
				class="absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-sidebar {status ===
				'authorized'
					? 'bg-foreground'
					: 'bg-muted-foreground/40'}"
			></span>
		{/if}
	</span>
{/snippet}

{#snippet body()}
	<span class="flex min-w-0 flex-1 flex-col">
		<span class="truncate text-sm leading-tight font-medium">{m.account_platform()}</span>
		<span class="truncate text-xs leading-tight text-muted-foreground">
			{statusLabel}
		</span>
	</span>

	<ChevronsUpDown class="size-3.5 shrink-0 text-muted-foreground" />
{/snippet}

{#if status === "loading"}
	<!-- Скелетон ровно той же высоты, что и живая ячейка: раскладка не дёргается. -->
	<div class="flex h-[52px] items-center gap-2.5 rounded-xl border px-2.5">
		<div class="size-7 shrink-0 animate-pulse rounded-full bg-muted"></div>
		<div class="flex flex-1 flex-col gap-1.5">
			<div class="h-2.5 w-14 animate-pulse rounded bg-muted"></div>
			<div class="h-2 w-20 animate-pulse rounded bg-muted"></div>
		</div>
	</div>
{:else if status === "offline"}
	<!--
		Бэкенд недоступен: ячейка статична и без действия (клик всё равно не
		дошёл бы), приглушена opacity + cursor-default — сигнал «не сейчас».
		Иконка связи, а не пользователя: проблема в канале, а не в аккаунте.
		Постоянный баннер сверху объясняет «почему» подробнее.
	-->
	<div
		class="flex h-[52px] items-center gap-2.5 rounded-xl border px-2.5 opacity-70 cursor-default select-none"
		aria-label={m.account_status_offline()}
	>
		<span
			class="flex size-7 shrink-0 items-center justify-center rounded-full border bg-muted"
		>
			<WifiOff class="size-[15px] text-muted-foreground" />
		</span>
		{@render body()}
	</div>

{:else if status === "authorized"}
	<!--
		Signing out is destructive (drops the persistent hh.ru session — the
		whole sign-in flow has to happen again), so it must NOT fire on a bare
		click of the cell. The chevron already promises a menu; now it opens
		one, and «Выйти» is the only thing in it.
	-->
	<DropdownMenu>
		<DropdownMenuTrigger
			aria-label={ariaLabel}
			class="flex h-[52px] w-full items-center gap-2.5 rounded-xl border px-2.5 text-left transition-colors hover:bg-accent data-[state=open]:bg-accent"
		>
			{@render avatar()}
			{@render body()}
		</DropdownMenuTrigger>
		<DropdownMenuContent align="start">
			<DropdownMenuItem onSelect={onSignOut}>{m.account_sign_out()}</DropdownMenuItem>
		</DropdownMenuContent>
	</DropdownMenu>
{:else}
	<button
		type="button"
		onclick={activate}
		aria-label={ariaLabel}
		class="flex h-[52px] w-full items-center gap-2.5 rounded-xl border px-2.5 text-left transition-colors hover:bg-accent"
	>
		{@render avatar()}
		{@render body()}
	</button>
{/if}
