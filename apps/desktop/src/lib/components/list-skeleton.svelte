<script lang="ts">
import { Skeleton } from "$lib/components/ui/skeleton";

interface Props {
	rows?: number;
}

const { rows = 3 }: Props = $props();
</script>

<!--
	Mirrors vacancy-card's geometry (border + p-4 + a left column of three
	stacked lines and a right rail), so the real list drops into exactly the
	space the skeleton held. Swapping a bare `<p>Загрузка…</p>` for this is what
	removes the layout jump on queue / vacancies / history.
-->
<ul class="space-y-3" aria-hidden="true">
    {#each Array.from({ length: rows }, (_, index) => index) as row (row)}
        <li class="bg-card flex items-start gap-4 rounded-lg border p-4">
            <div class="min-w-0 flex-1 space-y-2">
                <Skeleton class="h-5 w-3/4"/>
                <Skeleton class="h-4 w-1/3"/>
                <Skeleton class="h-4 w-1/4"/>
            </div>
            <Skeleton class="size-4 shrink-0"/>
        </li>
    {/each}
</ul>
