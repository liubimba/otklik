<script lang="ts">
import AppMark from "$lib/components/app-mark.svelte";
import * as m from "$lib/paraglide/messages";
import Copy from "@lucide/svelte/icons/copy";
import Minus from "@lucide/svelte/icons/minus";
import Square from "@lucide/svelte/icons/square";
import X from "@lucide/svelte/icons/x";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { platform } from "@tauri-apps/plugin-os";
import { onMount } from "svelte";

const isMac = platform() === "macos";

const appWindow = getCurrentWindow();
let maximized = $state(false);

onMount(() => {
	if (isMac) return;
	let unlisten: (() => void) | undefined;
	const sync = () => {
		appWindow.isMaximized().then((v) => {
			maximized = v;
		});
	};
	sync();
	appWindow.onResized(sync).then((fn) => {
		unlisten = fn;
	});
	return () => unlisten?.();
});

const controlClass =
	"text-muted-foreground inline-flex h-9 w-11 items-center justify-center transition-colors [&_svg]:size-4";
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	data-tauri-drag-region
	ondblclick={isMac ? undefined : () => appWindow.toggleMaximize()}
	class="bg-background flex h-9 shrink-0 items-center justify-between border-b select-none"
>
	<div class="flex items-center gap-2 px-3 {isMac ? 'pl-20' : ''}">
		<span
			class="bg-primary text-primary-foreground flex size-6 shrink-0 items-center justify-center rounded-md"
		>
			<AppMark class="size-4" />
		</span>
		<span class="font-mono text-sm font-semibold">{m.nav_app_title()}</span>
	</div>

	{#if !isMac}
		<div class="flex items-center">
			<button
				type="button"
				onclick={() => appWindow.minimize()}
				aria-label={m.window_minimize()}
				class="{controlClass} hover:bg-muted"
			>
				<Minus />
			</button>
			<button
				type="button"
				onclick={() => appWindow.toggleMaximize()}
				aria-label={maximized ? m.window_restore() : m.window_maximize()}
				class="{controlClass} hover:bg-muted"
			>
				{#if maximized}
					<Copy />
				{:else}
					<Square />
				{/if}
			</button>
			<button
				type="button"
				onclick={() => appWindow.close()}
				aria-label={m.window_close()}
				class="{controlClass} hover:bg-primary hover:text-primary-foreground"
			>
				<X />
			</button>
		</div>
	{/if}
</div>
