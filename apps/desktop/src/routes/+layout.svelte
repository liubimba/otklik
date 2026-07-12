<script lang="ts">
import { page } from "$app/state";
import { EventsWebSocket } from "$lib/api/events";
import type { ServerEvent } from "$lib/api/types";
import ProfileButton from "$lib/components/ProfileButton.svelte";
import DottedBackground from "$lib/components/dotted-background.svelte";
import { Button } from "$lib/components/ui/button";
import Separator from "$lib/components/ui/separator/separator.svelte";
import { Toaster } from "$lib/components/ui/sonner";
import WindowResizeHandles from "$lib/components/window-resize-handles.svelte";
import WindowTitlebar from "$lib/components/window-titlebar.svelte";
import * as m from "$lib/paraglide/messages";
import Briefcase from "@lucide/svelte/icons/briefcase";
import History from "@lucide/svelte/icons/history";
import Inbox from "@lucide/svelte/icons/inbox";
import Info from "@lucide/svelte/icons/info";
import Moon from "@lucide/svelte/icons/moon";
import Settings from "@lucide/svelte/icons/settings";
import Sun from "@lucide/svelte/icons/sun";
import {
	QueryClient,
	QueryClientProvider,
	notifyManager,
} from "@tanstack/svelte-query";
import { ModeWatcher, mode, toggleMode } from "mode-watcher";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";
import LetterReviewSheet from "$lib/components/letter-review-sheet.svelte";
// noinspection ES6UnusedImports
import * as Sidebar from "$lib/components/ui/sidebar";
import UpdateDialog from "$lib/components/update-dialog.svelte";
import { query } from "$lib/queries";
import { updater } from "$lib/stores/updater.svelte";

const { children }: LayoutProps = $props();

// The dotted canvas reads `--border` off the document, so it must be told when
// the theme flips. `dark` is a change signal, not a colour.
const dark = $derived(mode.current === "dark");

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			retry: 1,
			// Tauri is a long-lived desktop shell — refocusing the
			// window shouldn't trigger a refetch of every stale
			// query. We keep the cache warm and let WS events plus
			// explicit invalidations drive updates.
			refetchOnWindowFocus: false,
			// WS reconnect is a *real* connectivity restore signal
			// (unlike focus), and it fires infrequently, so always
			// refresh — including still-fresh queries.
			refetchOnReconnect: "always",
		},
	},
});

const items = [
	{
		title: m.nav_queue,
		href: "/queue",
		icon: Inbox,
	},
	{
		title: m.nav_vacancies,
		href: "/vacancies",
		icon: Briefcase,
	},
	{
		title: m.nav_history,
		href: "/history",
		icon: History,
	},
	{
		title: m.nav_settings,
		href: "/settings",
		icon: Settings,
	},
	{
		title: m.nav_about,
		href: "/about",
		icon: Info,
	},
];

onMount(() => {
	// Silent update check on launch. It never throws (no feed yet, offline, …);
	// if an update is found, <UpdateDialog/> pops up on its own via the store.
	void updater.check();

	const listener = new EventsWebSocket((event: ServerEvent) => {
		// A single WS event can trigger multiple cache mutations
		// (setQueryData + invalidateQueries). Without batching,
		// subscribers re-render once per mutation. `notifyManager.batch`
		// collapses them into one notification per event, keeping the
		// vacancy list / letter sheet from thrashing during an
		// auto-submit storm.
		notifyManager.batch(() => {
			switch (event.type) {
				case "vacancy_new":
					query.vacancies.apply(queryClient, event);
					query.all_vacancies.invalidate(queryClient);
					query.summary.invalidate(queryClient);
					break;
				case "search_event":
					query.search.vacancies.apply(queryClient, event);
					query.search.history.apply(queryClient, event);
					break;
				case "auth_changed":
					query.auth.apply(queryClient, event);
					break;
				case "application_event":
					query.application.apply(queryClient, event);
					// The archive page renders status inline from the list payload,
					// so only a list refetch can move its badges.
					query.all_vacancies.invalidate(queryClient);
					query.summary.invalidate(queryClient);
			}
		});
	});
	listener.connect();
	return () => {
		listener.close();
	};
});
</script>

<!--
    `.dark` and its full token block existed since day one, but nothing ever
    mounted ModeWatcher or offered a control — dark mode was unreachable.
-->
<ModeWatcher/>

<QueryClientProvider client={queryClient}>
    <Toaster richColors/>
    <LetterReviewSheet/>
    <UpdateDialog/>
    <WindowResizeHandles/>

    <!--
        Desktop shell: pinned to the viewport, no document scroll. The titlebar is
        full-window chrome above the sidebar+content row; that row fills the rest
        and scrolls internally (see the content wrapper below).
    -->
    <div class="flex h-svh flex-col overflow-hidden">
        <WindowTitlebar/>

        <Sidebar.Provider class="min-h-0 flex-1">
            <!--
                The inset sidebar is `fixed inset-y-0`, anchored to the viewport,
                so it has to be told to start below the h-9 (2.25rem) titlebar
                instead of at the very top edge. The brand now lives in the
                titlebar, so Sidebar.Header is gone.
            -->
            <Sidebar.Root variant="inset" class="top-9 h-[calc(100svh-2.25rem)]">
                <Sidebar.Content>
                <Sidebar.Group>
                    <Sidebar.GroupLabel>{m.nav_section_label()}</Sidebar.GroupLabel>
                    <Sidebar.Menu class="gap-1">
                        {#each items as item (item.href)}
                            <Sidebar.MenuItem>
                                <Sidebar.MenuButton
                                        isActive={page.url.pathname === item.href}
                                        tooltipContent={item.title()}
                                >
                                    {#snippet child({props})}
                                        <a href={item.href} {...props}>
                                            <item.icon/>
                                            <span>{item.title()}</span>
                                        </a>
                                    {/snippet}
                                </Sidebar.MenuButton>
                            </Sidebar.MenuItem>
                        {/each}
                    </Sidebar.Menu>
                </Sidebar.Group>
            </Sidebar.Content>

            <Sidebar.Footer class="border-t">
                <div class="flex items-center justify-between px-2 py-1.5">
                    <ProfileButton/>
                    <Button
                            variant="ghost"
                            size="icon-sm"
                            onclick={toggleMode}
                            aria-label={mode.current === "dark"
                                ? m.theme_switch_to_light()
                                : m.theme_switch_to_dark()}
                    >
                        {#if mode.current === "dark"}
                            <Sun/>
                        {:else}
                            <Moon/>
                        {/if}
                    </Button>
                </div>
            </Sidebar.Footer>

            <Sidebar.Rail/>
        </Sidebar.Root>

        <Sidebar.Inset>
            <header
                    class="sticky top-0 flex h-14 items-center gap-2 border-b px-4 bg-background z-20"
            >
                <Sidebar.Trigger/>
                <Separator orientation="vertical" class="h-4"/>
            </header>
            <!--
                Animated dotted canvas, app-wide. It is pinned to the content
                viewport (it does NOT scroll — the list scrolls above it) and
                scoped to this region so it never repaints under the sidebar or
                titlebar. The canvas only redraws on mouse movement, so scrolling
                a long list costs nothing; it self-gates on prefers-reduced-motion.
            -->
            <div class="relative min-h-0 flex-1">
                <DottedBackground {dark}/>
                <div class="absolute inset-0 overflow-y-auto">
                    {@render children()}
                </div>
            </div>
        </Sidebar.Inset>
    </Sidebar.Provider>
    </div>
</QueryClientProvider>
