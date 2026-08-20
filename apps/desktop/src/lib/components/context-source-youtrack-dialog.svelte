<script lang="ts">
import type { ContextSourceWrite } from "$lib/api/types";
import { Button } from "$lib/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "$lib/components/ui/dialog";
import { Input } from "$lib/components/ui/input";
import { Label } from "$lib/components/ui/label";
import { m } from "$lib/paraglide/messages";

type AddMutation = {
	mutate: (
		body: ContextSourceWrite,
		options?: { onSuccess?: () => void },
	) => void;
	isPending: boolean;
};

const DEFAULT_QUERY = "for: me";

let {
	open = $bindable(false),
	add,
}: {
	open?: boolean;
	add: AddMutation;
} = $props();

let label = $state("");
let baseUrl = $state("");
let token = $state("");
let query = $state(DEFAULT_QUERY);
let description = $state("");

function resetFields() {
	label = "";
	baseUrl = "";
	token = "";
	query = DEFAULT_QUERY;
	description = "";
}

function canSubmit(): boolean {
	return (
		label.trim().length > 0 &&
		baseUrl.trim().length > 0 &&
		token.trim().length > 0 &&
		query.trim().length > 0
	);
}

function submit() {
	if (!canSubmit()) return;
	add.mutate(
		{
			kind: "youtrack",
			label: label.trim(),
			description: description.trim() || null,
			config: { base_url: baseUrl.trim(), query: query.trim() },
			token: token.trim(),
		},
		{
			onSuccess: () => {
				resetFields();
				open = false;
			},
		},
	);
}
</script>

<Dialog bind:open>
	<DialogContent>
		<DialogHeader>
			<DialogTitle>{m.settings_ai_sources_youtrack_title()}</DialogTitle>
			<DialogDescription>
				{m.settings_ai_sources_youtrack_description()}
			</DialogDescription>
		</DialogHeader>

		<div class="space-y-3">
			<div class="space-y-1.5">
				<Label for="youtrack-source-label">
					{m.settings_ai_sources_label_field()}
				</Label>
				<Input id="youtrack-source-label" bind:value={label} />
			</div>
			<div class="space-y-1.5">
				<Label for="youtrack-source-base-url">
					{m.settings_ai_sources_youtrack_base_url_field()}
				</Label>
				<Input id="youtrack-source-base-url" type="url" bind:value={baseUrl} />
			</div>
			<div class="space-y-1.5">
				<Label for="youtrack-source-token">
					{m.settings_ai_sources_youtrack_token_field()}
				</Label>
				<Input id="youtrack-source-token" type="password" bind:value={token} />
			</div>
			<div class="space-y-1.5">
				<Label for="youtrack-source-query">
					{m.settings_ai_sources_youtrack_query_field()}
				</Label>
				<Input id="youtrack-source-query" bind:value={query} />
			</div>
			<div class="space-y-1.5">
				<Label for="youtrack-source-description">
					{m.settings_ai_sources_description_field()}
				</Label>
				<Input id="youtrack-source-description" bind:value={description} />
			</div>
		</div>

		<DialogFooter>
			<Button type="button" variant="outline" onclick={() => (open = false)}>
				{m.settings_ai_sources_youtrack_cancel()}
			</Button>
			<Button
				type="button"
				onclick={submit}
				disabled={add.isPending || !canSubmit()}
			>
				{m.settings_ai_sources_youtrack_submit()}
			</Button>
		</DialogFooter>
	</DialogContent>
</Dialog>
