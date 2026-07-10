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
import * as m from "$lib/paraglide/messages";
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
    <DropdownMenuTrigger
            class="flex items-center gap-2"
            aria-label={m.profile_trigger_label()}
    >
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
            <DropdownMenuLabel>{m.profile_menu_label()}</DropdownMenuLabel>
            {#if authQuery.data?.status === "unauthorized" || !authQuery.data}
                <DropdownMenuItem onSelect={() => actions.auth.authenticate.mutateAsync()}>
                    {m.profile_sign_in()}
                </DropdownMenuItem>
            {:else if authQuery.data?.status === "authorizing"}
                <DropdownMenuItem disabled>{m.profile_authorizing()}</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => actions.auth.cancel.mutateAsync()}>
                    {m.profile_cancel()}
                </DropdownMenuItem>
            {:else if authQuery.data?.status === "authorized"}
                <DropdownMenuItem onSelect={() => actions.auth.unauthorize.mutateAsync()}>
                    {m.profile_sign_out()}
                </DropdownMenuItem>
            {:else}
                <DropdownMenuItem disabled>{m.profile_unknown_status()}</DropdownMenuItem>
            {/if}
        </DropdownMenuGroup>
    </DropdownMenuContent>
</DropdownMenu>
