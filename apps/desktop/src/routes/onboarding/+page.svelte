<script lang="ts">
import { goto } from "$app/navigation";
import { Button } from "$lib/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "$lib/components/ui/dialog";
import { saveConsent } from "$lib/consent";
import { getLogger } from "$lib/log";
import * as m from "$lib/paraglide/messages";
import { shell } from "$lib/shell";

const logger = getLogger("onboarding");

let saving = $state(false);
let saveError = $state<string | null>(null);

async function accept() {
	logger.info("User accepted the consent dialog");
	saving = true;
	saveError = null;
	try {
		logger.info("Saving user consent...");
		await saveConsent(true);
		logger.info(
			"Consent saved successfully. Navigating to the browser setup step.",
		);
		await goto("/onboarding/browser");
	} catch (err) {
		logger.error(`Error saving consent: ${err}`);
		saveError = err instanceof Error ? err.message : String(err);
	}
	saving = false;
}

function decline() {
	logger.error("User declined the consent dialog. Closing current window");
	shell().window.close();
}

function handleOpenChange(open: boolean) {
	if (!open) decline();
}
</script>

<Dialog open={true} onOpenChange={handleOpenChange}>
    <DialogContent
            interactOutsideBehavior="ignore"
            escapeKeydownBehavior="ignore"
    >
        <DialogHeader>
            <DialogTitle>{m.onboarding_title()}</DialogTitle>
            <DialogDescription>
                {m.onboarding_description()}
            </DialogDescription>
        </DialogHeader>

        <div class="space-y-3 text-sm">
            <p>
                {m.onboarding_risk_intro()}
                <strong>{m.onboarding_risk_tos()}</strong>{m.onboarding_risk_ban()}
            </p>
            <p>
                {m.onboarding_own_risk_intro()}
                <strong>{m.onboarding_own_risk_strong()}</strong>{m.onboarding_own_risk_rest()}
            </p>
            <p>{m.onboarding_confirm_note()}</p>
        </div>

        {#if saveError}
            <p
                    role="alert"
                    class="border-destructive/30 bg-destructive/10 text-destructive rounded-md border p-3 text-sm"
            >
                {m.onboarding_save_failed({error: saveError})}
            </p>
        {/if}

        <DialogFooter>
            <Button variant="outline" onclick={decline} disabled={saving}>
                {m.onboarding_decline()}
            </Button>
            <Button onclick={accept} disabled={saving}>
                {saving ? m.onboarding_saving() : m.onboarding_accept()}
            </Button>
        </DialogFooter>
    </DialogContent>
</Dialog>
