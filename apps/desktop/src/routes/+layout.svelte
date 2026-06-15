<script lang="ts">
import { page } from "$app/state";
import { connectEvents } from "$lib/api/events";
import type { ServerEvent } from "$lib/api/types";
import ProfileButton from "$lib/components/ProfileButton.svelte";
import Separator from "$lib/components/ui/separator/separator.svelte";
import * as Sidebar from "$lib/components/ui/sidebar";
import { Toaster } from "$lib/components/ui/sonner";
import * as m from "$lib/paraglide/messages";
import { applyCurrentSearchEvent } from "$lib/queries/search";
import { applySearchEvent, applyVacancyEvent } from "$lib/queries/vacancies";
import { auth } from "$lib/stores/auth.svelte";
import { Inbox, Settings } from "@lucide/svelte";
import { QueryClient, QueryClientProvider } from "@tanstack/svelte-query";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";

const { children }: LayoutProps = $props();

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			retry: 1,
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
		title: m.nav_settings,
		href: "/settings",
		icon: Settings,
	},
];

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
									{#snippet child({ props })}
										<a href={item.href} {...props}>
											<item.icon />
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
					<ProfileButton />
				</div>
			</Sidebar.Footer>

			<Sidebar.Rail />
		</Sidebar.Root>

		<Sidebar.Inset>
			<header
				class="sticky top-0 flex h-14 items-center gap-2 border-b px-4 bg-background z-10"
			>
				<Sidebar.Trigger />
				<Separator orientation="vertical" class="h-4" />
			</header>
			<div class="flex-1">
				{@render children()}
			</div>
		</Sidebar.Inset>
	</Sidebar.Provider>
</QueryClientProvider>
