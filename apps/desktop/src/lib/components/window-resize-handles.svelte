<script lang="ts">
import { getCurrentWindow } from "@tauri-apps/api/window";
import { platform } from "@tauri-apps/plugin-os";

// Dropping the native frame (decorations: false) also drops the OS resize
// borders on Linux/GTK and Windows, so we restore them with thin edge/corner
// grips that hand the drag back to the compositor. macOS keeps its native
// frame, so no grips there.
const isMac = platform() === "macos";
const appWindow = getCurrentWindow();

// `ResizeDirection` isn't exported from the window module, so derive it from
// the method signature instead of restating the union.
type ResizeDirection = Parameters<typeof appWindow.startResizeDragging>[0];

function resize(direction: ResizeDirection) {
	return (e: MouseEvent) => {
		if (e.button !== 0) return; // left button only
		appWindow.startResizeDragging(direction);
	};
}
</script>

{#if !isMac}
	<!-- Transparent overlay: only the grips catch the pointer; everything else
	     (titlebar drag region, content) stays clickable through it. -->
	<div class="pointer-events-none fixed inset-0 z-30" aria-hidden="true">
		<!-- edges -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute inset-x-2 top-0 h-1 cursor-ns-resize"
			onmousedown={resize("North")}
		></div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute inset-x-2 bottom-0 h-1 cursor-ns-resize"
			onmousedown={resize("South")}
		></div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute inset-y-2 left-0 w-1 cursor-ew-resize"
			onmousedown={resize("West")}
		></div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute inset-y-2 right-0 w-1 cursor-ew-resize"
			onmousedown={resize("East")}
		></div>
		<!-- corners -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute top-0 left-0 size-2 cursor-nwse-resize"
			onmousedown={resize("NorthWest")}
		></div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute top-0 right-0 size-2 cursor-nesw-resize"
			onmousedown={resize("NorthEast")}
		></div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute bottom-0 left-0 size-2 cursor-nesw-resize"
			onmousedown={resize("SouthWest")}
		></div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="pointer-events-auto absolute right-0 bottom-0 size-2 cursor-nwse-resize"
			onmousedown={resize("SouthEast")}
		></div>
	</div>
{/if}
