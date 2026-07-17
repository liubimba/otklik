<script lang="ts">
import { createEventSync } from "$lib/api/event-sync";
import { EventsWebSocket } from "$lib/api/events";
import AppSidebar from "$lib/components/app-sidebar.svelte";
import ConnectionBanner from "$lib/components/connection-banner.svelte";
import DottedBackground from "$lib/components/dotted-background.svelte";
import { Toaster } from "$lib/components/ui/sonner";
import WindowResizeHandles from "$lib/components/window-resize-handles.svelte";
import WindowTitlebar from "$lib/components/window-titlebar.svelte";
import { QueryClient, QueryClientProvider } from "@tanstack/svelte-query";
import { ModeWatcher, mode } from "mode-watcher";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";
import LetterReviewSheet from "$lib/components/letter-review-sheet.svelte";
import UpdateDialog from "$lib/components/update-dialog.svelte";
import { updater } from "$lib/stores/updater.svelte";

const { children }: LayoutProps = $props();

const dark = $derived(mode.current === "dark");

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			retry: 1,
			refetchOnWindowFocus: false,
			refetchOnReconnect: "always",
		},
	},
});

onMount(() => {
	void updater.check();

	const sync = createEventSync(queryClient);
	const listener = new EventsWebSocket(
		sync.onEvent,
		undefined,
		undefined,
		undefined,
		sync.onConnect,
		sync.onDisconnect,
	);
	listener.connect();
	return () => {
		listener.close();
	};
});
</script>

<ModeWatcher/>

<QueryClientProvider client={queryClient}>
    <Toaster richColors/>
    <LetterReviewSheet/>
    <UpdateDialog/>
    <WindowResizeHandles/>

    <div class="flex h-svh flex-col overflow-hidden">
        <WindowTitlebar/>

        <ConnectionBanner/>

        <div class="relative flex min-h-0 flex-1">
            <DottedBackground {dark}/>

            <AppSidebar/>

            <main class="relative min-w-0 flex-1 overflow-y-auto">
                {@render children()}
            </main>
        </div>
    </div>
</QueryClientProvider>
