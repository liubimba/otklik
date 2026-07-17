<script lang="ts">
import type { LLMDeploymentForm } from "$lib/schemas/settings";
import { settingsFormSchema } from "$lib/schemas/settings";
import { zod4 } from "sveltekit-superforms/adapters";
import { defaults, superForm } from "sveltekit-superforms/client";
// Test-only wrapper: superForm() calls onDestroy() internally and can only
// run inside an active Svelte component's initialisation — so it can't be
// constructed directly in a .test.ts file's top-level code (unlike
// $lib/queries, which we stub instead of wiring a real QueryClientProvider,
// there is no stubbing superForm(): SettingsAiTab needs a real SuperForm
// instance to bind against). Same shape as
// src/routes/vacancies/page-harness.svelte.
import SettingsAiTab from "./settings-ai-tab.svelte";

interface Props {
	deployments: LLMDeploymentForm[];
}

const { deployments }: Props = $props();

const initial = defaults(zod4(settingsFormSchema));
initial.data.llm.deployments = deployments;
const form = superForm(initial, {
	SPA: true,
	dataType: "json",
	validators: zod4(settingsFormSchema),
});
</script>

<SettingsAiTab {form} />
