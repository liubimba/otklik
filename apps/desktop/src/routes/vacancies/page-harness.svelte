<script lang="ts">
import { type QueryClient, QueryClientProvider } from "@tanstack/svelte-query";
import Page from "./+page.svelte";

const { queryClient }: { queryClient: QueryClient } = $props();
</script>

<QueryClientProvider client={queryClient}>
    <Page/>
</QueryClientProvider>
