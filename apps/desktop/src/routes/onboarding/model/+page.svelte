<script lang="ts">
import { goto } from "$app/navigation";
import LiveStatus from "$lib/components/live-status.svelte";
import { Badge } from "$lib/components/ui/badge";
import { Button } from "$lib/components/ui/button";
import { Input } from "$lib/components/ui/input";
import { Separator } from "$lib/components/ui/separator";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import ArrowLeft from "@lucide/svelte/icons/arrow-left";
import ChevronRight from "@lucide/svelte/icons/chevron-right";
import CircleAlert from "@lucide/svelte/icons/circle-alert";
import CircleCheck from "@lucide/svelte/icons/circle-check";
import Cloud from "@lucide/svelte/icons/cloud";
import Cpu from "@lucide/svelte/icons/cpu";
import Download from "@lucide/svelte/icons/download";
import Gauge from "@lucide/svelte/icons/gauge";
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
import PenLine from "@lucide/svelte/icons/pen-line";
import Play from "@lucide/svelte/icons/play";
import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
import { useQueryClient } from "@tanstack/svelte-query";
import { onMount } from "svelte";
import { SetupViewModel } from "./setup.viewmodel.svelte";

const OLLAMA_DOWNLOAD_URL = "https://ollama.com/download";

// Мастер пишет deployment мимо формы Настроек, поэтому кэш ["settings"]
// (staleTime: Infinity) надо обновить руками его же ответом — иначе в
// Настройках модель не появится до перезапуска приложения.
const queryClient = useQueryClient();
const vm = new SetupViewModel((settings) =>
	queryClient.setQueryData(query.settings.key, settings),
);

onMount(() => vm.init());

// Ключ и признак «облако прошло» живут на странице, а не в машине: submitKey
// уже вернул true и записал deployment — флаг лишь переключает вид на общий
// экран «Готово», не трогая состояние CloudFlow (там так и остаётся "trial").
let keyInput = $state("");
let cloudDone = $state(false);

async function goLocal(): Promise<void> {
	await vm.chooseLocal();
}

async function goCloud(): Promise<void> {
	// Повторный вход в облако не должен унаследовать «done» от прошлой попытки.
	cloudDone = false;
	keyInput = "";
	await vm.chooseCloud();
}

async function checkKey(): Promise<void> {
	if (await vm.cloud.submitKey(keyInput)) cloudDone = true;
}

// Письмо — общий для обеих веток артефакт: локальный замер или облачный trial,
// смотря какой путь довёл до «Готово».
const letter = $derived(vm.local.letter ?? vm.cloud.letter);

// «Готово» — это не отдельный path, а терминальный экран внутри ветки:
// локальная машина доходит до screen==="done", облачная — до успешного
// submitKey (cloudDone), при котором CloudFlow остаётся на "trial".
const isDone = $derived(
	(vm.path === "local" && vm.local.screen === "done") ||
		(vm.path === "cloud" && cloudDone),
);

// Проценты и секунды приходят дробными — округляем один раз здесь, чтобы
// цифра в тексте и ширина полосы не разъезжались.
const percent = $derived(Math.round(vm.local.percent));
const seconds = $derived(Math.round(vm.local.seconds));

// Экран сам ничего не решает — вся логика в машинах. Прогресс шага озвучивается
// ридеру через <LiveStatus>: смена состояния видна глазами, но не слышна иначе.
const liveStatus = $derived.by(() => {
	if (isDone) return m.setup_done_title();
	if (vm.path === "choose") return m.setup_choose_title();
	if (vm.path === "local") {
		switch (vm.local.screen) {
			case "checking":
				return m.setup_checking();
			case "ollama-missing":
				return m.setup_ollama_missing_title();
			case "ollama-stopped":
				return m.setup_ollama_stopped_title();
			case "local-select":
				return m.setup_local_select_title();
			case "pull":
				return m.setup_pull_progress({ percent });
			case "benchmark":
				return m.setup_benchmark_title();
			case "done":
				return m.setup_done_title();
			case "too-slow":
				return m.setup_slow_title();
			case "error":
				return m.setup_error({ error: vm.local.errorMessage ?? "" });
		}
	}
	switch (vm.cloud.screen) {
		case "select":
			return m.setup_cloud_select_title();
		case "key":
			return m.setup_cloud_key_title({ model: vm.cloud.selected?.label ?? "" });
		case "trial":
			return m.setup_cloud_trial_progress();
		case "error":
			return m.setup_error({ error: vm.cloud.errorMessage ?? "" });
	}
	return "";
});
</script>

<div class="container mx-auto flex min-h-full max-w-xl flex-col justify-center gap-6 p-6">
    <header class="flex items-center justify-between gap-3">
        <p class="text-muted-foreground font-mono text-xs uppercase tracking-wide">
            {m.setup_title()}
        </p>
        <!--
            «Назад» уводит к развилке, а не назад по истории браузера: внутри
            ветки идти «на шаг раньше» некуда — машина состояний не хранит стек.
            На choose кнопки нет (уходить некуда), на done — тоже (шаг завершён).
        -->
        {#if vm.path !== "choose" && !isDone}
            <Button
                    variant="ghost"
                    size="sm"
                    class="text-muted-foreground -mr-2 cursor-pointer gap-1"
                    onclick={() => vm.back()}
            >
                <ArrowLeft class="size-4"/>
                {m.setup_back()}
            </Button>
        {/if}
    </header>

    <LiveStatus text={liveStatus}/>

    {#if isDone}
        <!--
            Общий финал обеих веток. Письмо — главный экран онбординга: обещание
            продукта здесь доказывается, а не декларируется, поэтому оно на виду
            целиком, а не спрятано за кнопкой «показать».
        -->
        <section class="bg-card space-y-4 rounded-lg border p-6 shadow-[var(--elevation-1)]">
            <div class="flex items-start gap-3">
                <CircleCheck class="text-primary size-5 shrink-0"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_done_title()}</h1>
                    <p class="text-muted-foreground text-sm">
                        {#if vm.path === "local" && letter}
                            {m.setup_done_body({ seconds })}
                        {:else}
                            {m.setup_done_already_configured()}
                        {/if}
                    </p>
                </div>
            </div>
            {#if letter}
                <div class="space-y-2">
                    <p class="text-muted-foreground text-xs" id="setup-letter-label">
                        {m.setup_letter_label()}
                    </p>
                    <p
                            aria-labelledby="setup-letter-label"
                            class="bg-muted/40 max-h-64 overflow-y-auto rounded-md border p-4 text-sm leading-relaxed whitespace-pre-wrap"
                    >{letter}</p>
                </div>
            {/if}
            <Button class="cursor-pointer" onclick={() => goto("/queue")}>
                {m.setup_done_continue()}
            </Button>
        </section>

    {:else if vm.path === "choose"}
        <!--
            Развилка: обе карточки равноправны, ни одна не «правильная». Клик по
            всей карточке (не только по кнопке) — цель крупнее 44px и очевиднее.
        -->
        <section class="space-y-4">
            <div class="space-y-1">
                <h1 class="text-lg font-semibold">{m.setup_choose_title()}</h1>
                {#if vm.currentModel}
                    <p class="text-muted-foreground text-xs">
                        {m.setup_choose_current({ model: vm.currentModel })}
                    </p>
                {/if}
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
                <button
                        type="button"
                        onclick={goLocal}
                        class="bg-card hover:border-primary/60 hover:bg-accent/40 focus-visible:ring-ring group flex cursor-pointer flex-col gap-3 rounded-lg border p-5 text-left shadow-[var(--elevation-1)] transition-colors focus-visible:ring-2 focus-visible:outline-none"
                >
                    <div class="flex items-center justify-between">
                        <Cpu class="text-primary size-6 shrink-0"/>
                        {#if vm.hardwareWeak}
                            <Badge variant="outline" class="text-muted-foreground gap-1 text-xs font-normal">
                                <TriangleAlert class="size-3"/>
                                {m.setup_choose_weak_badge()}
                            </Badge>
                        {/if}
                    </div>
                    <div class="space-y-1">
                        <p class="font-medium">{m.setup_choose_local()}</p>
                        <p class="text-muted-foreground text-sm">{m.setup_choose_local_hint()}</p>
                    </div>
                </button>

                <button
                        type="button"
                        onclick={goCloud}
                        class="bg-card hover:border-primary/60 hover:bg-accent/40 focus-visible:ring-ring group flex cursor-pointer flex-col gap-3 rounded-lg border p-5 text-left shadow-[var(--elevation-1)] transition-colors focus-visible:ring-2 focus-visible:outline-none"
                >
                    <Cloud class="text-primary size-6 shrink-0"/>
                    <div class="space-y-1">
                        <p class="font-medium">{m.setup_choose_cloud()}</p>
                        <p class="text-muted-foreground text-sm">{m.setup_choose_cloud_hint()}</p>
                    </div>
                </button>
            </div>
        </section>

    {:else}
        <!--
            Один контейнер на все экраны ветки: карточка не «прыгает» между
            состояниями шага, меняется только её содержимое.
        -->
        <section class="bg-card space-y-4 rounded-lg border p-6 shadow-[var(--elevation-1)]">
            {#if vm.path === "local"}
                {#if vm.local.screen === "checking"}
                    <div class="flex items-center gap-3">
                        <Cpu class="text-muted-foreground size-5 shrink-0 motion-safe:animate-pulse"/>
                        <p class="text-sm">{m.setup_checking()}</p>
                    </div>

                {:else if vm.local.screen === "local-select"}
                    <div class="space-y-2">
                        <h1 class="text-lg font-semibold">{m.setup_local_select_title()}</h1>
                    </div>
                    {#if vm.local.installedModels.length > 0}
                        <div class="space-y-2">
                            <p class="text-muted-foreground text-xs">
                                {m.setup_local_select_installed()}
                            </p>
                            <div class="space-y-2">
                                {#each vm.local.installedModels as tag (tag)}
                                    <button
                                            type="button"
                                            onclick={() => vm.local.selectInstalled(tag)}
                                            class="hover:border-primary/60 hover:bg-accent/40 focus-visible:ring-ring flex w-full cursor-pointer items-center justify-between gap-3 rounded-md border p-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
                                    >
                                        <span class="font-mono text-sm">{tag}</span>
                                        <ChevronRight class="text-muted-foreground size-4 shrink-0"/>
                                    </button>
                                {/each}
                            </div>
                        </div>
                    {/if}
                    <!--
                        «Установить рекомендованную» стартует загрузку 4.7 ГБ:
                        disabled на isPulling запирает вторую параллельную
                        загрузку поверх идущей.
                    -->
                    <Button
                            variant="outline"
                            class="w-full cursor-pointer gap-2"
                            disabled={vm.local.isPulling}
                            onclick={() => vm.local.installRecommended()}
                    >
                        <Download class="size-4"/>
                        {m.setup_local_select_install_recommended({ tag: vm.local.recommendedTag })}
                    </Button>

                {:else if vm.local.screen === "ollama-missing"}
                    <div class="flex items-start gap-3">
                        <Download class="text-muted-foreground size-5 shrink-0"/>
                        <div class="space-y-2">
                            <h1 class="text-lg font-semibold">{m.setup_ollama_missing_title()}</h1>
                            <p class="text-muted-foreground text-sm">{m.setup_ollama_missing_body()}</p>
                        </div>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <!--
                            Установка Ollama — вне приложения, поэтому ссылка —
                            настоящий <a>: opener открывает её в системном браузере.
                        -->
                        <Button href={OLLAMA_DOWNLOAD_URL} target="_blank" rel="noopener noreferrer">
                            {m.setup_install_link()}
                        </Button>
                        <Button variant="outline" class="cursor-pointer" onclick={() => vm.local.refresh()}>
                            {m.setup_recheck()}
                        </Button>
                    </div>

                {:else if vm.local.screen === "ollama-stopped"}
                    <div class="flex items-start gap-3">
                        <Play class="text-muted-foreground size-5 shrink-0"/>
                        <div class="space-y-2">
                            <h1 class="text-lg font-semibold">{m.setup_ollama_stopped_title()}</h1>
                            <p class="text-muted-foreground text-sm">{m.setup_ollama_stopped_body()}</p>
                        </div>
                    </div>
                    <Button class="cursor-pointer" onclick={() => vm.local.refresh()}>
                        {m.setup_recheck()}
                    </Button>

                {:else if vm.local.screen === "pull"}
                    <div class="space-y-2">
                        <h1 class="text-lg font-semibold">{m.setup_pull_title()}</h1>
                        <p class="text-muted-foreground font-mono text-sm">
                            {m.setup_pull_progress({ percent })}
                        </p>
                    </div>
                    <!--
                        Полоса показывает реальные проценты из стрима, а не
                        бесконечную крутилку: скачивание идёт минутами, и
                        пользователь должен видеть, что оно движется.
                    -->
                    <div
                            role="progressbar"
                            aria-label={m.setup_progress_label()}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={percent}
                            class="bg-muted h-2 w-full overflow-hidden rounded-full"
                    >
                        <div
                                class="bg-primary h-full rounded-full motion-safe:transition-[width] motion-safe:duration-300"
                                style="width: {percent}%"
                        ></div>
                    </div>

                {:else if vm.local.screen === "benchmark"}
                    <div class="flex items-start gap-3">
                        <Gauge class="text-muted-foreground size-5 shrink-0 motion-safe:animate-pulse"/>
                        <div class="space-y-2">
                            <h1 class="text-lg font-semibold">{m.setup_benchmark_title()}</h1>
                            <p class="text-muted-foreground text-sm">{m.setup_benchmark_body()}</p>
                        </div>
                    </div>

                {:else if vm.local.screen === "too-slow"}
                    <div class="flex items-start gap-3">
                        <PenLine class="text-muted-foreground size-5 shrink-0"/>
                        <div class="space-y-2">
                            <h1 class="text-lg font-semibold">{m.setup_slow_title()}</h1>
                            <p class="text-muted-foreground text-sm">{m.setup_slow_body()}</p>
                        </div>
                    </div>
                    <!--
                        Медленно — развилка, а не авария: «остаться» пишет
                        deployment, «Назад» (в шапке) уводит на выбор облака.
                    -->
                    <Button
                            variant="outline"
                            class="cursor-pointer"
                            onclick={() => vm.local.keepLocal()}
                    >
                        {m.setup_slow_keep_local()}
                    </Button>

                {:else if vm.local.screen === "error"}
                    <div class="flex items-start gap-3">
                        <CircleAlert class="text-destructive size-5 shrink-0"/>
                        <p class="text-destructive text-sm" role="alert">
                            {m.setup_error({ error: vm.local.errorMessage ?? "" })}
                        </p>
                    </div>
                    <Button variant="outline" class="cursor-pointer" onclick={() => vm.local.refresh()}>
                        {m.setup_retry()}
                    </Button>
                {/if}

            {:else if vm.cloud.screen === "select"}
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_cloud_select_title()}</h1>
                </div>
                <Input
                        type="search"
                        value={vm.cloud.query}
                        oninput={(e) => vm.cloud.setQuery(e.currentTarget.value)}
                        placeholder={m.setup_cloud_search_placeholder()}
                        aria-label={m.setup_cloud_search_placeholder()}
                />
                <div class="max-h-72 space-y-2 overflow-y-auto">
                    {#each vm.cloud.filtered as option (option.model)}
                        <button
                                type="button"
                                onclick={() => vm.cloud.choose(option)}
                                class="hover:border-primary/60 hover:bg-accent/40 focus-visible:ring-ring flex w-full cursor-pointer items-center justify-between gap-3 rounded-md border p-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
                        >
                            <span class="min-w-0 space-y-0.5">
                                <span class="block truncate text-sm font-medium">{option.label}</span>
                                <span class="text-muted-foreground block truncate text-xs">{option.provider}</span>
                            </span>
                            <ChevronRight class="text-muted-foreground size-4 shrink-0"/>
                        </button>
                    {/each}
                </div>

            {:else if vm.cloud.screen === "key"}
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">
                        {m.setup_cloud_key_title({ model: vm.cloud.selected?.label ?? "" })}
                    </h1>
                    {#if vm.cloud.selected?.key_url}
                        <a
                                href={vm.cloud.selected.key_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="text-primary text-sm underline-offset-4 hover:underline"
                        >
                            {m.setup_cloud_key_get()}
                        </a>
                    {/if}
                </div>
                <Input
                        type="password"
                        bind:value={keyInput}
                        placeholder={m.setup_cloud_key_placeholder()}
                        aria-label={m.setup_cloud_key_placeholder()}
                />
                {#if vm.cloud.errorMessage}
                    <p class="text-destructive text-sm" role="alert">
                        {m.setup_error({ error: vm.cloud.errorMessage })}
                    </p>
                {/if}
                <div class="flex flex-wrap gap-2">
                    <!--
                        disabled на isSubmitting запирает второй сабмит поверх
                        идущего trial'а.
                    -->
                    <Button
                            class="cursor-pointer"
                            disabled={vm.cloud.isSubmitting}
                            onclick={checkKey}
                    >
                        {m.setup_cloud_key_check()}
                    </Button>
                    {#if vm.cloud.errorMessage}
                        <Button
                                variant="outline"
                                class="cursor-pointer"
                                onclick={() => vm.cloud.backToSelect()}
                        >
                            {m.setup_cloud_pick_another()}
                        </Button>
                    {/if}
                </div>

            {:else if vm.cloud.screen === "trial"}
                <div class="flex items-center gap-3">
                    <LoaderCircle class="text-muted-foreground size-5 shrink-0 animate-spin"/>
                    <p class="text-sm">{m.setup_cloud_trial_progress()}</p>
                </div>

            {:else if vm.cloud.screen === "error"}
                <div class="flex items-start gap-3">
                    <CircleAlert class="text-destructive size-5 shrink-0"/>
                    <p class="text-destructive text-sm" role="alert">
                        {m.setup_error({ error: vm.cloud.errorMessage ?? "" })}
                    </p>
                </div>
                <Button variant="outline" class="cursor-pointer" onclick={goCloud}>
                    {m.setup_retry()}
                </Button>
            {/if}
        </section>
    {/if}

    <!--
        Пути отхода — на каждом экране, кроме финала: шаг модели никогда не
        запирает пользователя, пока модель ещё не настроена. На «Готово» бежать
        уже некуда — обе ссылки вели бы туда же, куда «Начать поиск».
    -->
    {#if !isDone}
        <footer class="space-y-3">
            <Separator/>
            <div class="flex flex-wrap items-center justify-between gap-2">
                <Button
                        variant="link"
                        size="sm"
                        class="text-muted-foreground cursor-pointer px-0"
                        onclick={() => goto("/settings")}
                >
                    {m.setup_own_key()}
                </Button>
                <Button
                        variant="link"
                        size="sm"
                        class="text-muted-foreground cursor-pointer px-0"
                        onclick={() => goto("/")}
                >
                    {m.setup_later()}
                </Button>
            </div>
        </footer>
    {/if}
</div>
