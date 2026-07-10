<script lang="ts">
interface Props {
	text: string;
}

const { text }: Props = $props();
</script>

<!--
	Async progress in this app is conveyed purely visually — search counters, the
	picker's phase lines, "Отправляем отклик…". A polite live region re-announces
	`text` whenever it changes, without stealing focus. aria-atomic makes the
	reader speak the whole sentence rather than the diffed word.
-->
<div role="status" aria-live="polite" aria-atomic="true" class="sr-only">
    {text}
</div>
