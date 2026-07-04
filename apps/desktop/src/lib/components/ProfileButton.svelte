<script lang="ts">
import { createActions } from "$lib/actions";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuTrigger,
} from "$lib/components/ui/dropdown-menu";
import { query } from "$lib/queries";
// noinspection ES6UnusedImports
import LoaderCircle from "@lucide/svelte/icons/loader-circle";
// noinspection ES6UnusedImports
import User from "@lucide/svelte/icons/user";
// noinspection ES6UnusedImports
import UserCheck from "@lucide/svelte/icons/user-check";
import { useQueryClient } from "@tanstack/svelte-query";

const queryClient = useQueryClient();
const authQuery = query.auth.create();
const actions = createActions(queryClient);
</script>

<DropdownMenu>
    <DropdownMenuTrigger class="flex items-center gap-2">
        {#if authQuery.data?.status === "authorized"}
            <UserCheck size={20}/>
        {:else if authQuery.data?.status === "authorizing"}
            <LoaderCircle size={20} class="animate-spin"/>
        {:else}
            <User size={20}/>
        {/if}
    </DropdownMenuTrigger>
    <DropdownMenuContent>
        <DropdownMenuGroup>
            <DropdownMenuLabel>hh.ru</DropdownMenuLabel>
            {#if authQuery.data?.status === "unauthorized" || !authQuery.data}
                <DropdownMenuItem onSelect={() => actions.auth.authenticate.mutateAsync()}
                >Sign in hh.ru
                </DropdownMenuItem
                >
            {:else if authQuery.data?.status === "authorizing"}
                <DropdownMenuItem disabled>Authorizing...</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => actions.auth.cancel.mutateAsync()}>Cancel</DropdownMenuItem>
            {:else if authQuery.data?.status === "authorized"}
                <DropdownMenuItem onSelect={() => actions.auth.unauthorize.mutateAsync()}>Sign out hh.ru
                </DropdownMenuItem>
            {:else}
                <DropdownMenuItem disabled>Unknown status</DropdownMenuItem>
            {/if}
        </DropdownMenuGroup>
    </DropdownMenuContent>
</DropdownMenu>
