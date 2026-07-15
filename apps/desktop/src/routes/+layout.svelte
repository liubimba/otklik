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

	// Вся синхронизация кэша с WS-потоком — в createEventSync (тестируется без
	// монтирования). onConnect помечает связь живой и ресинхронизирует auth +
	// сводку (в т.ч. чинит «вечный скелетон» профиля, если бэкенд поднялся
	// позже приложения); onDisconnect помечает связь оборванной → баннер и
	// приглушённые баджи.
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

        <!--
            Полоса «нет связи с бэкендом» — над рабочей областью, но под
            титлбаром: она часть хрома окна, а не контента. Сама рендерится
            только когда связь оборвана (см. компонент), поэтому в норме
            раскладка её не замечает.
        -->
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
