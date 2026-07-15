<script lang="ts">
import * as m from "$lib/paraglide/messages";
import { connection } from "$lib/stores/connection.svelte";
import WifiOff from "@lucide/svelte/icons/wifi-off";

// Показываемся только когда бэкенд ТОЧНО недоступен (`isOffline`), а не на
// начальном "connecting": иначе на каждом обычном запуске мигала бы «нет
// связи» на те доли секунды, пока сокет подключается.
const offline = $derived(connection.isOffline);
</script>

{#if offline}
	<!--
		Тонкая постоянная полоса под титлбаром — состояние длящееся, поэтому не
		тост (тот исчезает). Приглушённый муфтед-тон, единственный акцент палитры
		тут не к месту: это не призыв к действию, а фоновое «мы знаем, чиним».
		role="status" + aria-live=polite — ридер услышит появление, но не будет
		перебивать. Пульсирующая точка озвучивает «идёт переподключение» глазами.
	-->
	<div
		role="status"
		aria-live="polite"
		class="flex shrink-0 items-center justify-center gap-2 border-b bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground"
	>
		<WifiOff class="size-3.5 shrink-0" />
		<span>{m.connection_offline()}</span>
		<span
			class="size-1.5 shrink-0 rounded-full bg-muted-foreground/60 motion-safe:animate-pulse"
			aria-hidden="true"
		></span>
	</div>
{/if}
