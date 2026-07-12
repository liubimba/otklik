<script lang="ts">
import * as m from "$lib/paraglide/messages";
import ChevronsUpDown from "@lucide/svelte/icons/chevrons-up-down";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
import User from "@lucide/svelte/icons/user";

export type AuthStatus =
	| "loading"
	| "unauthorized"
	| "authorizing"
	| "authorized";

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
	}[status],
);

// Ячейка — это одна кнопка, но её действие зависит от состояния.
function activate() {
	if (status === "unauthorized") onSignIn();
	else if (status === "authorizing") onCancel();
	else if (status === "authorized") onSignOut();
}
</script>

{#if status === "loading"}
	<!-- Скелетон ровно той же высоты, что и живая ячейка: раскладка не дёргается. -->
	<div class="flex h-[52px] items-center gap-2.5 rounded-xl border px-2.5">
		<div class="size-7 shrink-0 animate-pulse rounded-full bg-muted"></div>
		<div class="flex flex-1 flex-col gap-1.5">
			<div class="h-2.5 w-14 animate-pulse rounded bg-muted"></div>
			<div class="h-2 w-20 animate-pulse rounded bg-muted"></div>
		</div>
	</div>
{:else}
	<button
		type="button"
		onclick={activate}
		class="flex h-[52px] w-full items-center gap-2.5 rounded-xl border px-2.5 text-left transition-colors hover:bg-accent"
	>
		<span class="relative flex size-7 shrink-0 items-center justify-center rounded-full border bg-muted">
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

		<span class="flex min-w-0 flex-1 flex-col">
			<span class="truncate text-sm leading-tight font-medium">{m.account_platform()}</span>
			<span class="truncate text-xs leading-tight text-muted-foreground">
				{statusLabel}
			</span>
		</span>

		<ChevronsUpDown class="size-3.5 shrink-0 text-muted-foreground" />
	</button>
{/if}
