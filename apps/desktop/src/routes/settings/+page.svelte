<script lang="ts">
import { API } from "$lib/api/client";
import SettingsAiTab from "$lib/components/settings-ai-tab.svelte";
import { Button } from "$lib/components/ui/button";
// noinspection ES6UnusedImports
import * as Form from "$lib/components/ui/form";
import { Input } from "$lib/components/ui/input";
import { Separator } from "$lib/components/ui/separator";
import { Skeleton } from "$lib/components/ui/skeleton";
import { Switch } from "$lib/components/ui/switch";
import { m } from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import { zform } from "$lib/schemas";
import {
	type LLMDeploymentForm,
	apiDeploymentToForm,
	formDeploymentToAPI,
} from "$lib/schemas/settings";
import { useQueryClient } from "@tanstack/svelte-query";
import { untrack } from "svelte";
import { toast } from "svelte-sonner";
import { defaults, superForm } from "sveltekit-superforms";
import { zod4 } from "sveltekit-superforms/adapters";

const queryClient = useQueryClient();
const settings = query.settings.create();

const form = superForm(defaults(zod4(zform.settings.schema)), {
	SPA: true,
	dataType: "json",
	resetForm: false,
	validators: zod4(zform.settings.schema),
	onUpdate: async ({ form }) => {
		if (!form.valid) {
			return;
		}
		try {
			const saved = await API.settings.update({
				search: form.data.search,
				user: form.data.user,
				rate_limits: form.data.rate_limits,
				llm: {
					resume_text: form.data.llm.resume_text,
					letter_style: form.data.llm.letter_style,
					system_prompt: form.data.llm.system_prompt.trim()
						? form.data.llm.system_prompt
						: null,
					deployments: form.data.llm.deployments.map(formDeploymentToAPI),
				},
			});
			queryClient.setQueryData(query.settings.key, saved);
			toast.success(m.settings_save_success());
		} catch (e) {
			const msg = e instanceof Error ? e.message : "unknown";
			toast.error(m.settings_save_failed({ error: msg }));
		}
	},
});
const { form: formData, enhance, submitting } = form;

$effect(() => {
	if (!settings.data) return;
	const existingDeployments = untrack(() => $formData.llm?.deployments ?? []);
	const deployments: LLMDeploymentForm[] = settings.data.llm.deployments.map(
		(d, i) => {
			const existingId = existingDeployments[i]?.id;
			const fresh = apiDeploymentToForm(d);
			return existingId ? { ...fresh, id: existingId } : fresh;
		},
	);

	formData.set({
		search: settings.data.search,
		user: settings.data.user,
		rate_limits: settings.data.rate_limits,
		llm: {
			resume_text: settings.data.llm.resume_text,
			letter_style: settings.data.llm.letter_style,
			system_prompt: settings.data.llm.system_prompt ?? "",
			deployments,
		},
	});
});
</script>

<div class="container mx-auto max-w-2xl p-6 space-y-6">
    <h1 class="text-2xl font-semibold">{m.settings_title()}</h1>

    {#if settings.isPending}
        <div class="space-y-6">
            {#each [0, 1, 2, 3, 4] as row (row)}
                <div class="space-y-2">
                    <Skeleton class="h-4 w-40 rounded"/>
                    <Skeleton class="h-9 w-full rounded-md"/>
                </div>
            {/each}
            <Skeleton class="h-9 w-32 rounded-md"/>
        </div>
    {:else if settings.isError}
        <div class="space-y-3">
            <p class="text-destructive">
                {m.settings_error_load({
                    error: settings.error?.message ?? "unknown",
                })}
            </p>
            <Button variant="outline" onclick={() => settings.refetch()}>
                {m.settings_error_retry()}
            </Button>
        </div>
    {:else}
        <form method="POST" use:enhance class="space-y-6">
            <section class="space-y-4">
                <div class="space-y-1">
                    <h2 class="text-lg font-medium">
                        {m.settings_section_automation()}
                    </h2>
                    <p class="text-sm text-muted-foreground">
                        {m.settings_section_automation_hint()}
                    </p>
                </div>

                    <Form.Field {form} name="search.max_pages">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_search_max_pages()}</Form.Label
                                >
                                <Input
                                        type="number"
                                        min="1"
                                        {...props}
                                        bind:value={$formData.search.max_pages}
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>

                    <Form.Field {form} name="search.max_vacancies">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_search_max_vacancies()}</Form.Label
                                >
                                <Input
                                        type="number"
                                        min="1"
                                        {...props}
                                        bind:value={$formData.search.max_vacancies}
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>
                    <Form.Field {form} name="user.auto_submit">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_user_auto_submit()}</Form.Label
                                >
                                <Form.Description
                                >{m.settings_user_auto_submit_hint()}</Form.Description
                                >
                                <Switch
                                        {...props}
                                        bind:checked={$formData.user.auto_submit}
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>
                <Separator/>
                <div class="space-y-1">
                    <h3 class="text-sm font-medium">
                        {m.settings_subsection_limits()}
                    </h3>
                    <p class="text-sm text-muted-foreground">
                        {m.settings_limits_description()}
                    </p>
                </div>

                    <Form.Field {form} name="rate_limits.hourly_limit">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_limits_hourly()}</Form.Label
                                >
                                <Input
                                        type="number"
                                        min="1"
                                        {...props}
                                        bind:value={
                                        $formData.rate_limits.hourly_limit
                                    }
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>

                    <Form.Field {form} name="rate_limits.daily_limit">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_limits_daily()}</Form.Label
                                >
                                <Input
                                        type="number"
                                        min="1"
                                        {...props}
                                        bind:value={
                                        $formData.rate_limits.daily_limit
                                    }
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>

                    <Form.Field {form} name="rate_limits.min_delay_ms">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_limits_min_delay()}</Form.Label
                                >
                                <Input
                                        type="number"
                                        min="0"
                                        {...props}
                                        bind:value={
                                        $formData.rate_limits.min_delay_ms
                                    }
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>

                    <Form.Field {form} name="rate_limits.delay_jitter_ms">
                        <Form.Control>
                            {#snippet children({props})}
                                <Form.Label
                                >{m.settings_limits_jitter()}</Form.Label
                                >
                                <Input
                                        type="number"
                                        min="0"
                                        {...props}
                                        bind:value={
                                        $formData.rate_limits.delay_jitter_ms
                                    }
                                />
                            {/snippet}
                        </Form.Control>
                        <Form.FieldErrors/>
                    </Form.Field>
            </section>

            <Separator/>

            <section class="space-y-4">
                <div class="space-y-1">
                    <h2 class="text-lg font-medium">
                        {m.settings_section_ai()}
                    </h2>
                    <p class="text-sm text-muted-foreground">
                        {m.settings_section_ai_hint()}
                    </p>
                </div>
                <SettingsAiTab {form}/>
            </section>

            <Button type="submit" disabled={$submitting}>
                {$submitting ? m.settings_saving() : m.settings_save()}
            </Button>
        </form>
    {/if}
</div>
