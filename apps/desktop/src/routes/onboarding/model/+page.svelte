<script lang="ts">
import { goto } from "$app/navigation";
import LiveStatus from "$lib/components/live-status.svelte";
import { Button } from "$lib/components/ui/button";
import { Separator } from "$lib/components/ui/separator";
import * as m from "$lib/paraglide/messages";
import { query } from "$lib/queries";
import CircleAlert from "@lucide/svelte/icons/circle-alert";
import CircleCheck from "@lucide/svelte/icons/circle-check";
import Cpu from "@lucide/svelte/icons/cpu";
import Download from "@lucide/svelte/icons/download";
import Gauge from "@lucide/svelte/icons/gauge";
import PenLine from "@lucide/svelte/icons/pen-line";
import Play from "@lucide/svelte/icons/play";
import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
import { useQueryClient } from "@tanstack/svelte-query";
import { onMount } from "svelte";
import { SetupViewModel } from "./setup.viewmodel.svelte";

const OLLAMA_DOWNLOAD_URL = "https://ollama.com/download";
// Настройки — одностраничные, без табов: секция AI живёт под этим id, якорь
// доводит фокус прямо до неё, а не до верха формы.
const SETTINGS_AI_ANCHOR = "/settings#settings-ai";

// Мастер пишет deployment мимо формы Настроек, поэтому кэш ["settings"]
// (staleTime: Infinity) надо обновить руками его же ответом — иначе в
// Настройках модель не появится до перезапуска приложения.
const queryClient = useQueryClient();
const vm = new SetupViewModel((settings) =>
	queryClient.setQueryData(query.settings.key, settings),
);

onMount(() => vm.refresh());

// Пресет облака пишет deployment сам — уводить на Настройки имеет смысл,
// только если запись реально прошла, иначе пользователь тихо потеряет
// причину провала (см. connectCloud()).
async function connectCloudAndGoToSettings(): Promise<void> {
	if (await vm.connectCloud()) await goto(SETTINGS_AI_ANCHOR);
}

// Проценты приходят дробными из стрима, а полоса и подпись читаются глазами —
// округляем один раз здесь, чтобы цифра в тексте и ширина полосы не разъезжались.
const percent = $derived(Math.round(vm.percent));
const seconds = $derived(Math.round(vm.seconds));

// Экран сам ничего не решает — вся логика в SetupViewModel. Здесь только
// разметка состояния и вызовы его методов. Прогресс шага озвучивается ридеру
// через <LiveStatus>: смена состояния видна глазами, но не слышна иначе.
const liveStatus = $derived.by(() => {
	switch (vm.screen) {
		case "checking":
			return m.setup_checking();
		case "weak-hardware":
			return m.setup_weak_title();
		case "ollama-missing":
			return m.setup_ollama_missing_title();
		case "ollama-stopped":
			return m.setup_ollama_stopped_title();
		case "pull":
			return m.setup_pull_progress({ percent });
		case "benchmark":
			return m.setup_benchmark_title();
		case "done":
			return m.setup_done_title();
		case "too-slow":
			return m.setup_slow_title();
		case "error":
			return m.setup_error({ error: vm.errorMessage ?? "" });
	}
});
</script>

<div class="container mx-auto flex min-h-full max-w-xl flex-col justify-center gap-6 p-6">
    <header class="space-y-1">
        <p class="text-muted-foreground font-mono text-xs uppercase tracking-wide">
            {m.setup_title()}
        </p>
        {#if vm.localModel}
            <p class="text-muted-foreground text-xs">
                {m.setup_model_label()}: <span class="font-mono">{vm.localModel}</span>
            </p>
        {/if}
    </header>

    <LiveStatus text={liveStatus}/>

    <!--
        Один контейнер на все девять состояний: карточка не «прыгает» между
        экранами шага, меняется только её содержимое.
    -->
    <section class="bg-card space-y-4 rounded-lg border p-6 shadow-[var(--elevation-1)]">
        {#if vm.screen === "checking"}
            <div class="flex items-center gap-3">
                <Cpu class="text-muted-foreground size-5 shrink-0 motion-safe:animate-pulse"/>
                <p class="text-sm">{m.setup_checking()}</p>
            </div>

        {:else if vm.screen === "weak-hardware"}
            <div class="flex items-start gap-3">
                <TriangleAlert class="text-destructive size-5 shrink-0"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_weak_title()}</h1>
                    <p class="text-muted-foreground text-sm">{m.setup_weak_body()}</p>
                </div>
            </div>
            <!--
                Облако — главный путь для слабого железа, поэтому оно primary.
                «Всё равно попробовать локально» остаётся рядом: гейт честный,
                но не запирающий.
            -->
            <div class="space-y-2">
                <Button
                        class="w-full cursor-pointer"
                        disabled={vm.isConnectingCloud}
                        onclick={connectCloudAndGoToSettings}
                >
                    {m.setup_weak_cloud()}
                </Button>
                <p class="text-muted-foreground text-xs">{m.setup_weak_cloud_note()}</p>
            </div>
            <Button
                    variant="outline"
                    class="w-full cursor-pointer"
                    onclick={() => vm.useLocalAnyway()}
            >
                {m.setup_weak_local_anyway()}
            </Button>

        {:else if vm.screen === "ollama-missing"}
            <div class="flex items-start gap-3">
                <Download class="text-muted-foreground size-5 shrink-0"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_ollama_missing_title()}</h1>
                    <p class="text-muted-foreground text-sm">{m.setup_ollama_missing_body()}</p>
                </div>
            </div>
            <div class="flex flex-wrap gap-2">
                <!--
                    Установка Ollama происходит вне приложения, поэтому ссылка —
                    настоящий <a>: плагин opener открывает её в системном браузере.
                -->
                <Button href={OLLAMA_DOWNLOAD_URL} target="_blank" rel="noopener noreferrer">
                    {m.setup_install_link()}
                </Button>
                <Button variant="outline" class="cursor-pointer" onclick={() => vm.refresh()}>
                    {m.setup_recheck()}
                </Button>
            </div>

        {:else if vm.screen === "ollama-stopped"}
            <div class="flex items-start gap-3">
                <Play class="text-muted-foreground size-5 shrink-0"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_ollama_stopped_title()}</h1>
                    <p class="text-muted-foreground text-sm">{m.setup_ollama_stopped_body()}</p>
                </div>
            </div>
            <Button class="cursor-pointer" onclick={() => vm.refresh()}>
                {m.setup_recheck()}
            </Button>

        {:else if vm.screen === "pull"}
            <div class="space-y-2">
                <h1 class="text-lg font-semibold">{m.setup_pull_title()}</h1>
                <p class="text-muted-foreground font-mono text-sm">
                    {m.setup_pull_progress({ percent })}
                </p>
            </div>
            <!--
                Полоса показывает реальные проценты из стрима, а не бесконечную
                крутилку: скачивание идёт минутами, и пользователь должен видеть,
                что оно движется. Ширина, а не transform: полоса — единственная
                анимация на экране, экономить кадры не на чем.
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
            <!--
                Без этой кнопки экран не сдвинуть: vm.pullModel() больше никак не
                вызвать. disabled завязан на isPulling — вторую загрузку поверх
                идущей не запустить.
            -->
            <Button
                    class="cursor-pointer"
                    disabled={vm.isPulling}
                    onclick={() => vm.pullModel()}
            >
                {m.setup_pull_button()}
            </Button>

        {:else if vm.screen === "benchmark"}
            <div class="flex items-start gap-3">
                <Gauge class="text-muted-foreground size-5 shrink-0 motion-safe:animate-pulse"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_benchmark_title()}</h1>
                    <p class="text-muted-foreground text-sm">{m.setup_benchmark_body()}</p>
                </div>
            </div>

        {:else if vm.screen === "done"}
            <div class="flex items-start gap-3">
                <CircleCheck class="text-primary size-5 shrink-0"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_done_title()}</h1>
                    <!--
                        Письмо есть только сразу после свежего замера — тогда и
                        секунды настоящие. Если сюда попали с уже настроенным
                        deployment'ом (повторный вход), letter пуст, а seconds
                        всегда 0: показывать «за 0 секунд» — значит врать.
                    -->
                    <p class="text-muted-foreground text-sm">
                        {#if vm.letter}
                            {m.setup_done_body({ seconds })}
                        {:else}
                            {m.setup_done_already_configured()}
                        {/if}
                    </p>
                </div>
            </div>
            <!--
                Письмо — главный экран онбординга: обещание продукта здесь
                доказывается, а не декларируется. Поэтому оно на виду, целиком,
                а не спрятано за кнопкой «показать».
            -->
            {#if vm.letter}
                <div class="space-y-2">
                    <p class="text-muted-foreground text-xs" id="setup-letter-label">
                        {m.setup_letter_label()}
                    </p>
                    <p
                            aria-labelledby="setup-letter-label"
                            class="bg-muted/40 max-h-64 overflow-y-auto rounded-md border p-4 text-sm leading-relaxed whitespace-pre-wrap"
                    >{vm.letter}</p>
                </div>
            {/if}
            <Button class="cursor-pointer" onclick={() => goto("/queue")}>
                {m.setup_done_continue()}
            </Button>

        {:else if vm.screen === "too-slow"}
            <div class="flex items-start gap-3">
                <PenLine class="text-muted-foreground size-5 shrink-0"/>
                <div class="space-y-2">
                    <h1 class="text-lg font-semibold">{m.setup_slow_title()}</h1>
                    <p class="text-muted-foreground text-sm">{m.setup_slow_body()}</p>
                </div>
            </div>
            <!--
                Медленно — это развилка, а не авария: обе ветки равноправны, поэтому
                обе кнопки одного веса, ни одна не «правильная». Письмо здесь не
                показываем: при таймауте бэкенд отменяет генерацию и всегда
                возвращает letter=null (services/backend .../setup/benchmark.py) —
                ветка с письмом была недостижима.
            -->
            <div class="flex flex-wrap gap-2">
                <Button
                        variant="outline"
                        class="cursor-pointer"
                        onclick={() => vm.keepLocal()}
                >
                    {m.setup_slow_keep_local()}
                </Button>
                <Button
                        class="cursor-pointer"
                        disabled={vm.isConnectingCloud}
                        onclick={connectCloudAndGoToSettings}
                >
                    {m.setup_weak_cloud()}
                </Button>
            </div>
            <p class="text-muted-foreground text-xs">{m.setup_weak_cloud_note()}</p>

        {:else if vm.screen === "error"}
            <div class="flex items-start gap-3">
                <CircleAlert class="text-destructive size-5 shrink-0"/>
                <p class="text-destructive text-sm" role="alert">
                    {m.setup_error({ error: vm.errorMessage ?? "" })}
                </p>
            </div>
            <Button variant="outline" class="cursor-pointer" onclick={() => vm.refresh()}>
                {m.setup_retry()}
            </Button>
        {/if}
    </section>

    <!--
        Пути отхода — вне карточки и на каждом экране без исключения, кроме
        "done": шаг модели никогда не запирает пользователя, пока модель ещё
        не настроена (P0-6). На готовом экране бежать уже некуда — обе ссылки
        вели бы туда же, куда и «Начать работу», и были бы просто шумом.
    -->
    {#if vm.screen !== "done"}
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
