<script lang="ts">
import type { ContextSource, ContextSourceWrite } from "$lib/api/types";
import { Badge } from "$lib/components/ui/badge";
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

type UpdateMutation = {
	mutate: (
		params: { id: number; body: ContextSourceWrite },
		options?: { onSuccess?: () => void },
	) => void;
	isPending: boolean;
};

type YoutrackConfig = { base_url?: string; query?: string };

const DEFAULT_QUERY = "for: me";

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
let baseUrl = $state("");
let token = $state("");
let query = $state(DEFAULT_QUERY);
let description = $state("");
let clearToken = $state(false);

$effect(() => {
	if (!open) return;
	if (source) {
		const config = source.config as YoutrackConfig | null;
		label = source.label;
		description = source.description ?? "";
		baseUrl = config?.base_url ?? "";
		query = config?.query ?? DEFAULT_QUERY;
		token = "";
		clearToken = false;
	} else {
		label = "";
		baseUrl = "";
		token = "";
		query = DEFAULT_QUERY;
		description = "";
		clearToken = false;
	}
});

function resetFields() {
	label = "";
	baseUrl = "";
	token = "";
	query = DEFAULT_QUERY;
	description = "";
	clearToken = false;
}

function canSubmit(): boolean {
	const base =
		label.trim().length > 0 &&
		baseUrl.trim().length > 0 &&
		query.trim().length > 0;
	if (source) return base;
	return base && token.trim().length > 0;
}

function submit() {
	if (!canSubmit()) return;
	const trimmedLabel = label.trim();
	const trimmedBaseUrl = baseUrl.trim();
	const trimmedQuery = query.trim();
	const trimmedDescription = description.trim() || null;

	if (source) {
		update.mutate(
			{
				id: source.id,
				body: {
					kind: "youtrack",
					label: trimmedLabel,
					description: trimmedDescription,
					config: { base_url: trimmedBaseUrl, query: trimmedQuery },
					token: token.trim() || null,
					clear_token: clearToken,
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
			kind: "youtrack",
			label: trimmedLabel,
			description: trimmedDescription,
			config: { base_url: trimmedBaseUrl, query: trimmedQuery },
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
			<DialogTitle>
				{source
					? m.settings_ai_sources_youtrack_edit_title()
					: m.settings_ai_sources_youtrack_title()}
			</DialogTitle>
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
				<Input
					id="youtrack-source-base-url"
					type="url"
					bind:value={baseUrl}
					placeholder={m.settings_ai_sources_youtrack_base_url_hint()}
				/>
				<p class="text-muted-foreground text-xs">
					{m.settings_ai_sources_youtrack_base_url_hint()}
				</p>
			</div>
			<div class="space-y-1.5">
				<Label for="youtrack-source-token">
					{m.settings_ai_sources_youtrack_token_field()}
				</Label>
				{#if source?.has_token}
					<div>
						<Badge variant="secondary">
							{m.settings_ai_sources_youtrack_has_token()}
						</Badge>
					</div>
				{/if}
				<Input
					id="youtrack-source-token"
					type="password"
					bind:value={token}
					disabled={clearToken}
					placeholder={source
						? m.settings_ai_sources_youtrack_token_keep_placeholder()
						: undefined}
				/>
				{#if source?.has_token}
					<Label class="flex items-center gap-2 text-sm font-normal">
						<input type="checkbox" bind:checked={clearToken} />
						{m.settings_ai_sources_youtrack_clear_token()}
					</Label>
				{/if}
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
				disabled={(source ? update.isPending : add.isPending) || !canSubmit()}
			>
				{m.settings_ai_sources_youtrack_submit()}
			</Button>
		</DialogFooter>
	</DialogContent>
</Dialog>
