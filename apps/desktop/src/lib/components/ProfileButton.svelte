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
import ChevronsUpDown from "@lucide/svelte/icons/chevrons-up-down";
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

const status = $derived(authQuery.data?.status);
</script>

<DropdownMenu>
    <!--
        A real, tactile control: bordered surface, hover + open highlight, and a
        chevron to signal the menu. The status dot stays monochrome (the palette
        has no green) — solid when signed in, faint when not; a spinner replaces
        the icon while authorizing.
    -->
    <DropdownMenuTrigger
            class="flex items-center gap-1.5 rounded-lg border bg-sidebar px-2 py-1.5 text-sidebar-foreground transition-colors outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[state=open]:bg-sidebar-accent"
            aria-label={m.profile_trigger_label()}
    >
        <span class="relative flex size-5 items-center justify-center">
            {#if status === "authorized"}
                <UserCheck size={18}/>
            {:else if status === "authorizing"}
                <LoaderCircle size={18} class="animate-spin"/>
            {:else}
                <User size={18}/>
            {/if}
            {#if status !== "authorizing"}
                <span
                        class="border-sidebar absolute -right-0.5 -bottom-0.5 size-2 rounded-full border-2 {status ===
                        'authorized'
                            ? 'bg-foreground'
                            : 'bg-muted-foreground/40'}"
                ></span>
            {/if}
        </span>
        <ChevronsUpDown class="text-muted-foreground size-3.5"/>
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
