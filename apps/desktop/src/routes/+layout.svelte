<script lang="ts">
import { EventsWebSocket } from "$lib/api/events";
import type { ServerEvent } from "$lib/api/types";
import AppSidebar from "$lib/components/app-sidebar.svelte";
import DottedBackground from "$lib/components/dotted-background.svelte";
import { Toaster } from "$lib/components/ui/sonner";
import WindowResizeHandles from "$lib/components/window-resize-handles.svelte";
import WindowTitlebar from "$lib/components/window-titlebar.svelte";
import {
	QueryClient,
	QueryClientProvider,
	notifyManager,
} from "@tanstack/svelte-query";
import { ModeWatcher, mode } from "mode-watcher";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";
import LetterReviewSheet from "$lib/components/letter-review-sheet.svelte";
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
        and scrolls internally.

        The dotted canvas sits behind BOTH the sidebar and the content, in this
        shared flex row: the sidebar's notch is a hole in its own panel, and the
        canvas has to show through it, not just through the content area. The
        sidebar and `<main>` are each `relative` (position: relative), which
        keeps them painting above this absolutely-positioned canvas.
    -->
    <div class="flex h-svh flex-col overflow-hidden">
        <WindowTitlebar/>

        <div class="relative flex min-h-0 flex-1">
            <DottedBackground {dark}/>

            <AppSidebar/>

            <main class="relative min-w-0 flex-1 overflow-y-auto">
                {@render children()}
            </main>
        </div>
    </div>
</QueryClientProvider>
