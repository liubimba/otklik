<script lang="ts">
import ProfileButton from "$lib/components/ProfileButton.svelte";
import { auth } from "$lib/stores/auth.svelte";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";
import { connectEvents } from "$lib/api/events";
import type { ServerEvent } from "$lib/api/types";
import { Toaster } from "$lib/components/ui/sonner";
import { applyCurrentSearchEvent } from "$lib/queries/search";
import { applySearchEvent, applyVacancyEvent } from "$lib/queries/vacancies";
import { QueryClient, QueryClientProvider } from "@tanstack/svelte-query";

const { children }: LayoutProps = $props();

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			retry: 1,
		},
	},
});

onMount(() => {
	auth.fetchStatus();

	const ws = connectEvents((event: ServerEvent) => {
		switch (event.type) {
			case "vacancy_new":
				applyVacancyEvent(queryClient, event);
				break;
			case "search_event":
				applySearchEvent(queryClient, event);
				applyCurrentSearchEvent(queryClient, event);
				break;
			case "auth_changed":
				auth.applyAuthEvent(event);
				break;
		}
	});

	return () => {
		ws.close();
	};
});
</script>

<QueryClientProvider client={queryClient}>
    <Toaster richColors />
    <header class="flex justify-end">
        <ProfileButton />
    </header>
    {@render children()}
</QueryClientProvider>
