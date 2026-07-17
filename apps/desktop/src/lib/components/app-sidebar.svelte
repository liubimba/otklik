<script lang="ts">
import { page } from "$app/state";
import { createActions } from "$lib/actions";
import type { SummaryScope } from "$lib/api/types";
import AccountCell from "$lib/components/account-cell.svelte";
import {
	authCellStatus,
	badgeCount,
	guardedAuthAction,
} from "$lib/components/app-sidebar.logic";
import SidebarNavRow from "$lib/components/sidebar-nav-row.svelte";
import SidebarNotch from "$lib/components/sidebar-notch.svelte";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import { connection } from "$lib/stores/connection.svelte";
import type { Icon as IconType } from "@lucide/svelte";
import Briefcase from "@lucide/svelte/icons/briefcase";
import History from "@lucide/svelte/icons/history";
import Inbox from "@lucide/svelte/icons/inbox";
import Info from "@lucide/svelte/icons/info";
import Moon from "@lucide/svelte/icons/moon";
import Settings from "@lucide/svelte/icons/settings";
import Sun from "@lucide/svelte/icons/sun";
import { useQueryClient } from "@tanstack/svelte-query";
import { mode, toggleMode } from "mode-watcher";
import { toast } from "svelte-sonner";

type NavGroup = "work" | "config";
type NavItem = {
	href: string;
	label: string;
	icon: typeof IconType;
	group: NavGroup;
	scope?: SummaryScope;
};

const queryClient = useQueryClient();
const actions = createActions(queryClient);

const summaryAll = query.summary.create("all");
const summaryLatest = query.summary.create("latest");
const authQuery = query.auth.create();

const activePath = $derived(page.url.pathname);

const needsAttention: Record<SummaryScope, number | null> = $derived({
	all: summaryAll.data === undefined ? null : summaryAll.data.needs_attention,
	latest:
		summaryLatest.data === undefined
			? null
			: summaryLatest.data.needs_attention,
});

const authStatus = $derived(
	authCellStatus(connection.isOffline, authQuery.data),
);

const theme = $derived(mode.current === "dark" ? "dark" : "light");

const failToast = (message: string) =>
	toast.error(m.account_action_failed(), { description: message });
const onSignIn = () =>
	guardedAuthAction(() => actions.auth.authenticate.mutateAsync(), failToast);
const onSignOut = () =>
	guardedAuthAction(() => actions.auth.unauthorize.mutateAsync(), failToast);
const onCancelAuth = () =>
	guardedAuthAction(() => actions.auth.cancel.mutateAsync(), failToast);

const items: NavItem[] = $derived([
	{
		href: "/queue",
		label: m.nav_queue(),
		icon: Inbox,
		group: "work",
		scope: "latest",
	},
	{
		href: "/vacancies",
		label: m.nav_vacancies(),
		icon: Briefcase,
		group: "work",
		scope: "all",
	},
	{ href: "/history", label: m.nav_history(), icon: History, group: "work" },
	{
		href: "/settings",
		label: m.nav_settings(),
		icon: Settings,
		group: "config",
	},
	{ href: "/about", label: m.nav_about(), icon: Info, group: "config" },
]);

const groupLabels: Record<NavGroup, string> = $derived({
	work: m.nav_group_work(),
	config: m.nav_group_config(),
});

const groups = $derived([
	{ key: "work" as const, items: items.filter((i) => i.group === "work") },
	{ key: "config" as const, items: items.filter((i) => i.group === "config") },
]);

const W = 224;

// biome-ignore lint/style/useConst: bind:this reassigns this
let asideEl = $state<HTMLElement | undefined>(undefined);
// biome-ignore lint/style/useConst: bind:clientHeight reassigns this
let asideH = $state(0);
let notch = $state<{ top: number; h: number; left: number } | null>(null);

function measure() {
	if (!asideEl) return;
	const active = asideEl.querySelector<HTMLElement>('a[aria-current="page"]');
	if (!active) {
		notch = null;
		return;
	}
	const a = asideEl.getBoundingClientRect();
	const e = active.getBoundingClientRect();
	notch = { top: e.top - a.top, h: e.height, left: e.left - a.left };
}

$effect(() => {
	activePath;
	asideH;
	const id = requestAnimationFrame(measure);
	return () => cancelAnimationFrame(id);
});

$effect(() => {
	if (!asideEl) return;
	const ro = new ResizeObserver(() => measure());
	ro.observe(asideEl);
	return () => ro.disconnect();
});
</script>

<aside
	bind:this={asideEl}
	bind:clientHeight={asideH}
	class="relative m-3 flex w-56 shrink-0 flex-col"
>
	<SidebarNotch width={W} height={asideH} {notch} />

	<div class="relative z-10 flex flex-1 flex-col gap-1 p-3">
		<nav class="flex flex-1 flex-col gap-4">
			{#each groups as group (group.key)}
				<div class="flex flex-col gap-1">
					<p class="px-3 py-1 text-xs font-medium text-muted-foreground">
						{groupLabels[group.key]}
					</p>
					{#each group.items as item (item.href)}
						<SidebarNavRow
							href={item.href}
							label={item.label}
							icon={item.icon}
							active={activePath === item.href}
							count={badgeCount(
								connection.isOffline,
								item.scope ? needsAttention[item.scope] : null,
							)}
						/>
					{/each}
				</div>
			{/each}
		</nav>

		<div class="flex flex-col gap-2">
			<button
				type="button"
				onclick={toggleMode}
				class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
			>
				{#if theme === "dark"}
					<Sun class="size-[18px] shrink-0" />
					<span>{m.theme_switch_to_light()}</span>
				{:else}
					<Moon class="size-[18px] shrink-0" />
					<span>{m.theme_switch_to_dark()}</span>
				{/if}
			</button>

			<AccountCell status={authStatus} {onSignIn} {onSignOut} onCancel={onCancelAuth} />
		</div>
	</div>
</aside>
