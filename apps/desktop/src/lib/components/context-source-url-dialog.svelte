<script lang="ts">
import type { ContextSource, ContextSourceWrite } from "$lib/api/types";
import { Button } from "$lib/components/ui/button";
import {
	Dialog,
	DialogContent,
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

type UpdateMutation = {
	mutate: (
		params: { id: number; body: ContextSourceWrite },
		options?: { onSuccess?: () => void },
	) => void;
	isPending: boolean;
};

let {
	open = $bindable(false),
	add,
	update,
	source = null,
}: {
	open?: boolean;
	add: AddMutation;
	update: UpdateMutation;
	source?: ContextSource | null;
} = $props();

let label = $state("");
let url = $state("");
let description = $state("");

$effect(() => {
	if (!open) return;
	if (source) {
		label = source.label;
		url = source.url;
		description = source.description ?? "";
	} else {
		label = "";
		url = "";
		description = "";
	}
});

function resetFields() {
	label = "";
	url = "";
	description = "";
}

function kindForUrl(u: string): "github" | "web" {
	try {
		return new URL(u).host === "github.com" ? "github" : "web";
	} catch {
		return "web";
	}
}

function canSubmit(): boolean {
	return label.trim().length > 0 && url.trim().length > 0;
}

function submit() {
	if (!canSubmit()) return;
	const trimmedLabel = label.trim();
	const trimmedUrl = url.trim();
	const trimmedDescription = description.trim() || null;

	if (source) {
		update.mutate(
			{
				id: source.id,
				body: {
					label: trimmedLabel,
					kind: source.kind,
					url: trimmedUrl,
					description: trimmedDescription,
				},
			},
			{
				onSuccess: () => {
					resetFields();
					open = false;
				},
			},
		);
		return;
	}

	add.mutate(
		{
			label: trimmedLabel,
			kind: kindForUrl(trimmedUrl),
			url: trimmedUrl,
			description: trimmedDescription,
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
			<DialogTitle>
				{source
					? m.settings_ai_sources_url_dialog_edit_title()
					: m.settings_ai_sources_url_dialog_add_title()}
			</DialogTitle>
		</DialogHeader>

		<div class="space-y-3">
			<div class="space-y-1.5">
				<Label for="url-source-label">
					{m.settings_ai_sources_label_field()}
				</Label>
				<Input id="url-source-label" bind:value={label} />
			</div>
			<div class="space-y-1.5">
				<Label for="url-source-url">
					{m.settings_ai_sources_url_field()}
				</Label>
				<Input id="url-source-url" type="url" bind:value={url} />
			</div>
			<div class="space-y-1.5">
				<Label for="url-source-description">
					{m.settings_ai_sources_description_field()}
				</Label>
				<Input id="url-source-description" bind:value={description} />
			</div>
		</div>

		<DialogFooter>
			<Button type="button" variant="outline" onclick={() => (open = false)}>
				{m.settings_ai_sources_youtrack_cancel()}
			</Button>
			<Button
				type="button"
				onclick={submit}
				disabled={(source ? update.isPending : add.isPending) || !canSubmit()}
			>
				{source
					? m.settings_ai_sources_url_dialog_submit_edit()
					: m.settings_ai_sources_url_dialog_submit_add()}
			</Button>
		</DialogFooter>
	</DialogContent>
</Dialog>
