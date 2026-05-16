<script lang="ts">
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuTrigger,
} from "$lib/components/ui/dropdown-menu";
import { auth } from "$lib/stores/auth.svelte";
import { LoaderCircle, User, UserCheck } from "@lucide/svelte";

const status = $derived(auth.getState()?.status ?? null);
</script>

<DropdownMenu>
    <DropdownMenuTrigger class="flex items-center gap-2">
        {#if status === "authorized"}
            <UserCheck size={20} />
        {:else if status === "authorizing"}
            <LoaderCircle size={20} class="animate-spin" />
        {:else}
            <User size={20} />
        {/if}
    </DropdownMenuTrigger>
    <DropdownMenuContent>
        <DropdownMenuGroup>
            <DropdownMenuLabel>hh.ru</DropdownMenuLabel>
            {#if status === "unauthorized"}
                <DropdownMenuItem onSelect={() => auth.fetchAuthentication()}
                    >Sign in hh.ru</DropdownMenuItem
                >
            {:else if status == "authorizing"}
                <DropdownMenuItem disabled>Authorizing...</DropdownMenuItem>
            {:else if status == "authorized"}
                <DropdownMenuItem>Sign out hh.ru</DropdownMenuItem>
            {:else}
                <DropdownMenuItem disabled>Unknown status</DropdownMenuItem>
            {/if}
        </DropdownMenuGroup>
    </DropdownMenuContent>
</DropdownMenu>
