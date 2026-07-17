<script lang="ts">
interface Props {
	text: string;
}

const { text }: Props = $props();
</script>

<div role="status" aria-live="polite" aria-atomic="true" class="sr-only">
    {text}
</div>
