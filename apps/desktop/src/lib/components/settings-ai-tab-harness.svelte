<script lang="ts">
import type { LLMDeploymentForm } from "$lib/schemas/settings";
import { settingsFormSchema } from "$lib/schemas/settings";
import { zod4 } from "sveltekit-superforms/adapters";
import { defaults, superForm } from "sveltekit-superforms/client";
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
