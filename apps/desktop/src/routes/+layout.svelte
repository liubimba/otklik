<script lang="ts">
import { page } from "$app/state";
import { EventsWebSocket } from "$lib/api/events";
import type { ServerEvent } from "$lib/api/types";
import ProfileButton from "$lib/components/ProfileButton.svelte";
import Separator from "$lib/components/ui/separator/separator.svelte";
import { Toaster } from "$lib/components/ui/sonner";
import * as m from "$lib/paraglide/messages";
import Briefcase from "@lucide/svelte/icons/briefcase";
import History from "@lucide/svelte/icons/history";
import Inbox from "@lucide/svelte/icons/inbox";
import Settings from "@lucide/svelte/icons/settings";
import {
	QueryClient,
	QueryClientProvider,
	notifyManager,
} from "@tanstack/svelte-query";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";
import LetterReviewSheet from "$lib/components/letter-review-sheet.svelte";
// noinspection ES6UnusedImports
import * as Sidebar from "$lib/components/ui/sidebar";
import { query } from "$lib/queries";

const { children }: LayoutProps = $props();

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
];

onMount(() => {
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
			}
		});
	});
	listener.connect();
	return () => {
		listener.close();
	};
});
</script>

<QueryClientProvider client={queryClient}>
    <Toaster richColors/>
    <LetterReviewSheet/>

    <Sidebar.Provider>
        <Sidebar.Root variant="inset">
            <Sidebar.Header>
                <div class="px-2 py-1.5 text-sm font-semibold">
                    {m.nav_app_title()}
                </div>
            </Sidebar.Header>

            <Sidebar.Content>
                <Sidebar.Group>
                    <Sidebar.Menu>
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

            <Sidebar.Footer>
                <div class="flex items-center px-2 py-1.5">
                    <ProfileButton/>
                </div>
            </Sidebar.Footer>

            <Sidebar.Rail/>
        </Sidebar.Root>

        <Sidebar.Inset>
            <header
                    class="sticky top-0 flex h-14 items-center gap-2 border-b px-4 bg-background z-10"
            >
                <Sidebar.Trigger/>
                <Separator orientation="vertical" class="h-4"/>
            </header>
            <div class="flex-1">
                {@render children()}
            </div>
        </Sidebar.Inset>
    </Sidebar.Provider>
</QueryClientProvider>
