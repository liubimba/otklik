<script lang="ts">
import { createActions } from "$lib/actions";
import type {
	AICoverLetterResponse,
	PreviewCoverLetterRequest,
} from "$lib/api/types";
import EmptyState from "$lib/components/empty-state.svelte";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import { Input } from "$lib/components/ui/input";
import { Label } from "$lib/components/ui/label";
import { Textarea } from "$lib/components/ui/textarea";
import { notifySandboxLetter } from "$lib/notifications/notifier";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import FlaskConical from "@lucide/svelte/icons/flask-conical";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
import Sparkles from "@lucide/svelte/icons/sparkles";
import { useQueryClient } from "@tanstack/svelte-query";

const STORAGE_KEY = "otklik:playground:form";

type PlaygroundForm = {
	title: string;
	company_name: string;
	salary: string;
	work_location: string;
	work_experience: string;
	description: string;
};

const DEFAULT_FORM: PlaygroundForm = {
	title: "Backend-разработчик (Python)",
	company_name: "ООО «Технологии Будущего»",
	salary: "250 000 – 350 000 ₽ на руки",
	work_location: "Москва",
	work_experience: "От 3 до 6 лет",
	description: [
		"Ищем backend-разработчика для развития платформы обработки заказов.",
		"",
		"Обязанности:",
		"— проектирование и разработка REST API на FastAPI",
		"— работа с PostgreSQL, оптимизация запросов",
		"— код-ревью, менторство джунов",
		"",
		"Требования:",
		"— опыт коммерческой разработки на Python от 3 лет",
		"— знание asyncio, SQLAlchemy",
		"— опыт работы с очередями (Celery/RQ)",
		"",
		"Условия:",
		"— удалённая работа, гибкий график",
		"— ДМС, компенсация обучения",
	].join("\n"),
};

function loadStoredForm(): PlaygroundForm {
	if (typeof window === "undefined") return { ...DEFAULT_FORM };
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (!raw) return { ...DEFAULT_FORM };
		return { ...DEFAULT_FORM, ...JSON.parse(raw) };
	} catch {
		return { ...DEFAULT_FORM };
	}
}

const queryClient = useQueryClient();
const actions = createActions(queryClient).preview;
const settingsQuery = query.settings.create();

const form = $state<PlaygroundForm>(loadStoredForm());
let letterText = $state("");
let result = $state<AICoverLetterResponse | null>(null);

$effect(() => {
	const snapshot = JSON.stringify(form);
	if (typeof window === "undefined") return;
	window.localStorage.setItem(STORAGE_KEY, snapshot);
});

function buildRequest(): PreviewCoverLetterRequest {
	return {
		title: form.title,
		description: form.description,
		company_name: form.company_name.trim() || null,
		salary: form.salary.trim() || null,
		work_location: form.work_location.trim() || null,
		work_experience: form.work_experience.trim() || null,
	};
}

function generate(event: SubmitEvent) {
	event.preventDefault();
	actions.generate.mutate(buildRequest(), {
		onSuccess: (data) => {
			result = data;
			letterText = data.text;
			if (settingsQuery.data) {
				notifySandboxLetter(settingsQuery.data.notifications);
			}
		},
	});
}

const costLabel = $derived(
	result?.cost_usd != null ? `$${result.cost_usd.toFixed(4)}` : null,
);
</script>

<div class="container mx-auto max-w-4xl space-y-6 p-6">
	<div class="space-y-1">
		<h1 class="text-2xl font-semibold">{m.playground_title()}</h1>
		<p class="text-muted-foreground text-sm">{m.playground_hint()}</p>
	</div>

	<div class="grid gap-6 lg:grid-cols-2">
		<form onsubmit={generate} class="space-y-4 rounded-md border p-4">
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1.5">
					<Label for="playground-title">{m.playground_field_title()}</Label>
					<Input id="playground-title" bind:value={form.title} required />
				</div>
				<div class="space-y-1.5">
					<Label for="playground-company">
						{m.playground_field_company()}
					</Label>
					<Input id="playground-company" bind:value={form.company_name} />
				</div>
				<div class="space-y-1.5">
					<Label for="playground-salary">{m.playground_field_salary()}</Label>
					<Input id="playground-salary" bind:value={form.salary} />
				</div>
				<div class="space-y-1.5">
					<Label for="playground-location">
						{m.playground_field_location()}
					</Label>
					<Input id="playground-location" bind:value={form.work_location} />
				</div>
				<div class="space-y-1.5 sm:col-span-2">
					<Label for="playground-experience">
						{m.playground_field_experience()}
					</Label>
					<Input
						id="playground-experience"
						bind:value={form.work_experience}
					/>
				</div>
			</div>
			<div class="space-y-1.5">
				<Label for="playground-description">
					{m.playground_field_description()}
				</Label>
				<Textarea
					id="playground-description"
					bind:value={form.description}
					rows={12}
					required
				/>
			</div>
			<Button
				type="submit"
				disabled={actions.generate.isPending}
				class="w-full sm:w-auto"
			>
				{#if actions.generate.isPending}
					<LoaderCircle class="size-4 animate-spin" />
					{m.playground_generate_pending()}
				{:else}
					<Sparkles class="size-4" />
					{m.playground_generate()}
				{/if}
			</Button>
			{#if actions.generate.isError}
				<p class="text-destructive text-sm">
					{m.playground_generate_error({
						error: actions.generate.error?.message ?? "unknown",
					})}
				</p>
			{/if}
		</form>

		<div class="space-y-3 rounded-md border p-4">
			<p class="text-sm font-medium">{m.playground_result_heading()}</p>
			{#if result}
				<div class="space-y-1.5">
					<Label for="playground-result">
						{m.playground_result_label()}
					</Label>
					<Textarea id="playground-result" bind:value={letterText} rows={16} />
				</div>
				<div
					class="text-muted-foreground flex flex-wrap items-center gap-2 text-xs"
				>
					<span>{m.playground_meta_model({ model: result.model_used })}</span>
					<span>&middot;</span>
					<span>
						{m.playground_meta_tokens({ tokens: result.total_tokens })}
					</span>
					{#if costLabel}
						<span>&middot;</span>
						<span>{m.playground_meta_cost({ cost: costLabel })}</span>
					{/if}
					{#if result.was_fallback}
						<Badge variant="secondary">{m.playground_meta_fallback()}</Badge>
					{/if}
				</div>
			{:else}
				<EmptyState icon={FlaskConical} title={m.playground_result_empty()} />
			{/if}
		</div>
	</div>
</div>
