<script lang="ts">
import ProfileButton from "$lib/components/ProfileButton.svelte";
import { auth } from "$lib/stores/auth.svelte";
import { onMount } from "svelte";
import type { LayoutProps } from "./$types";
import "../app.css";

const { children }: LayoutProps = $props();

onMount(() => {
	auth.fetchStatus();
});
</script>

<header class="flex justify-end">
    <ProfileButton />
</header>

{@render children()}
