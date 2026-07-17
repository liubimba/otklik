<script lang="ts">
const { class: className = "size-6" }: { class?: string } = $props();
</script>

<svg
	viewBox="0 0 256 256"
	xmlns="http://www.w3.org/2000/svg"
	class={className}
	aria-hidden="true"
>
	<circle cx="128" cy="128" r="60" fill="none" stroke="currentColor" stroke-width="14" />
	<g fill="currentColor">
		<rect x="121" y="26" width="14" height="66" rx="7" />
		<rect x="121" y="164" width="14" height="66" rx="7" />
		<rect x="26" y="121" width="66" height="14" rx="7" />
		<rect x="164" y="121" width="66" height="14" rx="7" />
		<rect x="116" y="116" width="24" height="24" rx="6" />
	</g>
</svg>
