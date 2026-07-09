<script lang="ts">
// Test-only wrapper: the archive page needs a QueryClientProvider above it.
import { type QueryClient, QueryClientProvider } from "@tanstack/svelte-query";
import Page from "./+page.svelte";

const { queryClient }: { queryClient: QueryClient } = $props();
</script>

<QueryClientProvider client={queryClient}>
    <Page/>
</QueryClientProvider>
