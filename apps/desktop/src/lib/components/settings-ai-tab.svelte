<script lang="ts">
import { goto } from "$app/navigation";
import SortableDeployment from "$lib/components/sortable-deployment.svelte";
import * as Accordion from "$lib/components/ui/accordion";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import * as Form from "$lib/components/ui/form";
import { Input } from "$lib/components/ui/input";
import { Textarea } from "$lib/components/ui/textarea";
import { m } from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import {
	type LLMDeploymentForm,
	type SettingsFormData,
	makeDeploymentId,
} from "$lib/schemas/settings";
import { DragDropProvider } from "@dnd-kit/svelte";
import { isSortableOperation } from "@dnd-kit/svelte/sortable";
import GripVertical from "@lucide/svelte/icons/grip-vertical";
import Plus from "@lucide/svelte/icons/plus";
import Sparkles from "@lucide/svelte/icons/sparkles";
import Trash2 from "@lucide/svelte/icons/trash-2";
import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
import type { SuperForm } from "sveltekit-superforms";

interface Props {
	form: SuperForm<SettingsFormData>;
}

const { form }: Props = $props();
const { form: formData } = form;

// Режим хранения решается бэкендом один раз при старте (staleTime: Infinity
// в самом query) — предупреждение показываем только когда системной связки
// ключей нет и секреты лежат в файле.
const secretStorage = query.secret_storage.create();
const insecureStorage = $derived(secretStorage.data?.mode === "file");

// Та же кэш-запись, что читает /settings (staleTime: Infinity, тот же
// queryKey) — не отдельный запрос, а подписка на уже загруженные данные,
// нужная только чтобы поймать момент, когда ../routes/settings/+page.svelte
// перезаписывает кэш свежим (без ключей) ответом после Save.
const settings = query.settings.create();

let openItems = $state<string[]>([]);

// «Пользователь нажал Заменить» — состояние, которое не выразить через
// has_api_key/api_key/clear_api_key: буфер пуст и там, и в состоянии
// «ключ сохранён, не трогали» (см. keyFieldState ниже). Ключ карты — id
// deployment'а, тот же, что у visibleKeys раньше.
const replacingKey = $state<Record<string, boolean>>({});

$effect(() => {
	// Новые данные с бэкенда — первая загрузка или setQueryData после
	// успешного Save — закрывают режим «печатаем новый ключ» для всех строк.
	// Иначе после сохранения поле продолжало бы показывать (уже пустой)
	// инпут вместо «Ключ сохранён».
	settings.data;
	for (const id of Object.keys(replacingKey)) {
		delete replacingKey[id];
	}
});

type KeyFieldState = "stored" | "clearing" | "editing";

function keyFieldState(deployment: LLMDeploymentForm): KeyFieldState {
	if (deployment.clear_api_key) return "clearing";
	if (deployment.has_api_key && !replacingKey[deployment.id]) return "stored";
	return "editing";
}

function startReplacing(index: number) {
	const id = $formData.llm.deployments[index].id;
	replacingKey[id] = true;
}

function markCleared(index: number) {
	const id = $formData.llm.deployments[index].id;
	$formData.llm.deployments[index].clear_api_key = true;
	$formData.llm.deployments[index].api_key = "";
	delete replacingKey[id];
}

function cancelClear(index: number) {
	$formData.llm.deployments[index].clear_api_key = false;
}

function arrayMove<T>(arr: T[], from: number, to: number): T[] {
	const next = [...arr];
	const [moved] = next.splice(from, 1);
	next.splice(to, 0, moved);
	return next;
}

function handleDragEnd(event: {
	canceled: boolean;
	operation: { source: unknown; target: unknown };
}) {
	if (event.canceled) return;
	if (!isSortableOperation(event.operation as never)) return;
	const op = event.operation as {
		source: { id: string; index: number } | null;
		target: { id: string; index: number } | null;
	};
	const { source, target } = op;
	if (!source || !target || source.id === target.id) return;
	if (source.index === target.index) return;
	$formData.llm.deployments = arrayMove(
		$formData.llm.deployments,
		source.index,
		target.index,
	);
}

function addDeployment() {
	const created: LLMDeploymentForm = {
		id: makeDeploymentId(),
		model: "",
		api_base: "",
		has_api_key: false,
		api_key: "",
		clear_api_key: false,
	};
	$formData.llm.deployments = [...$formData.llm.deployments, created];
	openItems = [...openItems, created.id];
}

function removeDeployment(index: number) {
	const id = $formData.llm.deployments[index].id;
	$formData.llm.deployments = $formData.llm.deployments.filter(
		(_, i) => i !== index,
	);
	openItems = openItems.filter((v) => v !== id);
	delete replacingKey[id];
}

function deploymentBadge(index: number): string {
	if (index === 0) {
		return m.settings_ai_deployment_badge_primary();
	}
	return m.settings_ai_deployment_badge_fallback({ n: index });
}
</script>

<div class="space-y-6">
	<Form.Field {form} name="llm.resume_text">
		<Form.Control>
			{#snippet children({ props })}
				<Form.Label>{m.settings_ai_resume_label()}</Form.Label>
				<Form.Description>{m.settings_ai_resume_hint()}</Form.Description>
				<Textarea
					{...props}
					bind:value={$formData.llm.resume_text}
					rows={10}
				/>
			{/snippet}
		</Form.Control>
		<Form.FieldErrors />
	</Form.Field>

	<Form.Field {form} name="llm.letter_style">
		<Form.Control>
			{#snippet children({ props })}
				<Form.Label>{m.settings_ai_letter_style_label()}</Form.Label>
				<Form.Description>
					{m.settings_ai_letter_style_hint()}
				</Form.Description>
				<Input {...props} bind:value={$formData.llm.letter_style} />
			{/snippet}
		</Form.Control>
		<Form.FieldErrors />
	</Form.Field>

	<Form.Field {form} name="llm.system_prompt">
		<Form.Control>
			{#snippet children({ props })}
				<Form.Label>{m.settings_ai_system_prompt_label()}</Form.Label>
				<Form.Description>
					{m.settings_ai_system_prompt_hint()}
				</Form.Description>
				<Textarea
					{...props}
					bind:value={$formData.llm.system_prompt}
					rows={6}
				/>
			{/snippet}
		</Form.Control>
		<Form.FieldErrors />
	</Form.Field>

	<div class="space-y-3">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="space-y-1">
				<p class="text-sm font-medium">{m.settings_ai_deployments_label()}</p>
				<p class="text-muted-foreground text-sm">
					{m.settings_ai_deployments_hint()}
				</p>
			</div>
			<!--
				Тот же мастер, что и при первом онбординге (/onboarding/model).
				Он распознаёт не просто присутствие deployment'а в списке, а
				то, что им можно пользоваться (см. LLMDeployment.is_usable на
				бэкенде) — и в этом случае сразу схлопывается в экран «Готово»
				без путей назад. Возвращаться сюда имеет смысл, только пока шаг
				не завершён (например, облачный пресет записан с пустым
				ключом): сменить уже рабочий deployment или дописать к нему
				ключ через мастер нельзя — ключ вставляется прямо здесь, в
				форме ниже.
			-->
			<Button
				type="button"
				variant="outline"
				size="sm"
				class="shrink-0"
				onclick={() => goto("/onboarding/model")}
			>
				<Sparkles class="size-4" />
				{m.settings_ai_setup_wizard()}
			</Button>
		</div>

		{#if insecureStorage}
			<div
				class="border-amber-500/30 bg-amber-500/10 flex items-start gap-2 rounded-md border p-3 text-sm text-amber-700 dark:text-amber-400"
			>
				<TriangleAlert class="mt-0.5 size-4 shrink-0" />
				<p>{m.settings_ai_storage_file_warning()}</p>
			</div>
		{/if}

		{#if $formData.llm.deployments.length === 0}
			<p
				class="text-muted-foreground rounded-md border border-dashed p-6 text-center text-sm"
			>
				{m.settings_ai_deployments_empty()}
			</p>
		{:else}
			<DragDropProvider onDragEnd={handleDragEnd}>
				<Accordion.Root
					type="multiple"
					bind:value={openItems}
					class="space-y-2"
				>
					{#each $formData.llm.deployments as deployment, i (deployment.id)}
						<SortableDeployment id={deployment.id} index={i}>
							{#snippet children({ attachHandle })}
								<Accordion.Item
									value={deployment.id}
									class="overflow-hidden rounded-md border"
								>
									<div class="flex items-center gap-2 px-3 py-2">
										<span
											{@attach attachHandle}
											class="text-muted-foreground cursor-grab touch-none select-none active:cursor-grabbing"
											aria-label={m.settings_ai_drag_handle_label()}
										>
											<GripVertical class="size-4" />
										</span>
										<Accordion.Trigger
											class="flex flex-1 items-center gap-2 hover:no-underline"
										>
											<span class="truncate text-left">
												{deployment.model ||
													m.settings_ai_deployment_unnamed()}
											</span>
											<Badge variant="outline" class="ml-auto">
												{deploymentBadge(i)}
											</Badge>
										</Accordion.Trigger>
										<Button
											type="button"
											variant="ghost"
											size="icon"
											onclick={() => removeDeployment(i)}
											aria-label={m.settings_ai_delete_deployment()}
										>
											<Trash2 class="size-4" />
										</Button>
									</div>
									<Accordion.Content
										class="space-y-3 border-t px-3 py-3"
									>
										<Form.Field
											{form}
											name={`llm.deployments[${i}].model`}
										>
											<Form.Control>
												{#snippet children({ props })}
													<Form.Label>
														{m.settings_ai_deployment_model_label()}
													</Form.Label>
													<Form.Description>
														{m.settings_ai_deployment_model_hint()}
													</Form.Description>
													<Input
														{...props}
														bind:value={
															$formData.llm.deployments[i]
																.model
														}
														placeholder="openai/gpt-4o"
													/>
												{/snippet}
											</Form.Control>
											<Form.FieldErrors />
										</Form.Field>

										<Form.Field
											{form}
											name={`llm.deployments[${i}].api_key`}
										>
											<Form.Control>
												{#snippet children({ props })}
													<Form.Label>
														{m.settings_ai_deployment_api_key_label()}
													</Form.Label>
													<Form.Description>
														{m.settings_ai_deployment_api_key_hint()}
													</Form.Description>
													{#if keyFieldState(deployment) === "stored"}
														<!-- Бэкенд ключи больше не отдаёт — раскрывать
															 нечего, поэтому вместо Eye/EyeOff тут
															 статус и явные действия. -->
														<div
															class="flex items-center justify-between gap-2 rounded-md border p-3"
														>
															<span
																class="text-muted-foreground text-sm"
															>
																{m.settings_ai_key_stored()}
															</span>
															<div class="flex gap-2">
																<Button
																	type="button"
																	variant="outline"
																	size="sm"
																	class="cursor-pointer"
																	onclick={() =>
																		startReplacing(i)}
																>
																	{m.settings_ai_key_replace()}
																</Button>
																<Button
																	type="button"
																	variant="ghost"
																	size="sm"
																	class="cursor-pointer"
																	onclick={() =>
																		markCleared(i)}
																>
																	{m.settings_ai_key_remove()}
																</Button>
															</div>
														</div>
													{:else if keyFieldState(deployment) === "clearing"}
														<div
															class="border-destructive/30 bg-destructive/10 flex items-center justify-between gap-2 rounded-md border p-3"
														>
															<span
																class="text-destructive text-sm"
															>
																{m.settings_ai_key_will_be_removed()}
															</span>
															<Button
																type="button"
																variant="ghost"
																size="sm"
																class="cursor-pointer"
																onclick={() => cancelClear(i)}
															>
																{m.settings_ai_key_cancel_remove()}
															</Button>
														</div>
													{:else}
														<Input
															{...props}
															type="password"
															placeholder={m.settings_ai_key_placeholder()}
															bind:value={
																$formData.llm
																	.deployments[i]
																	.api_key
															}
														/>
													{/if}
												{/snippet}
											</Form.Control>
											<Form.FieldErrors />
										</Form.Field>

										<Form.Field
											{form}
											name={`llm.deployments[${i}].api_base`}
										>
											<Form.Control>
												{#snippet children({ props })}
													<Form.Label>
														{m.settings_ai_deployment_api_base_label()}
													</Form.Label>
													<Form.Description>
														{m.settings_ai_deployment_api_base_hint()}
													</Form.Description>
													<Input
														{...props}
														bind:value={
															$formData.llm.deployments[i]
																.api_base
														}
														placeholder="http://localhost:11434"
													/>
												{/snippet}
											</Form.Control>
											<Form.FieldErrors />
										</Form.Field>
									</Accordion.Content>
								</Accordion.Item>
							{/snippet}
						</SortableDeployment>
					{/each}
				</Accordion.Root>
			</DragDropProvider>
		{/if}

		<Button type="button" variant="outline" onclick={addDeployment}>
			<Plus class="size-4" />
			{m.settings_ai_add_deployment()}
		</Button>
	</div>
</div>
