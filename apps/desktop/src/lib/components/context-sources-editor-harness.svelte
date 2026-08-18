<script lang="ts">
import ContextSourcesEditor from "$lib/components/context-sources-editor.svelte";
import { QueryClient, QueryClientProvider } from "@tanstack/svelte-query";

const queryClient = new QueryClient({
	defaultOptions: { queries: { retry: false } },
});
</script>

<QueryClientProvider client={queryClient}>
	<ContextSourcesEditor />
</QueryClientProvider>
