<script lang="ts">
import { goto } from "$app/navigation";
import { page } from "$app/state";
import { Button } from "$lib/components/ui/button";
import CircleAlert from "@lucide/svelte/icons/circle-alert";
</script>

<div class="flex min-h-[60vh] flex-1 flex-col items-center justify-center gap-5 p-6 text-center">
	<CircleAlert class="text-destructive size-8" />
	<div class="space-y-2">
		<h1 class="text-lg font-semibold">Что-то пошло не так</h1>
		<p class="text-muted-foreground max-w-md text-sm break-words">
			{page.error?.message ?? "Неизвестная ошибка"}
		</p>
		{#if page.status}
			<p class="text-muted-foreground font-mono text-xs">код {page.status}</p>
		{/if}
	</div>
	<div class="flex flex-wrap justify-center gap-2">
		<Button
			variant="outline"
			class="cursor-pointer"
			onclick={() => location.reload()}
		>
			Перезагрузить
		</Button>
		<Button class="cursor-pointer" onclick={() => goto("/queue")}>
			На главную
		</Button>
	</div>
</div>
