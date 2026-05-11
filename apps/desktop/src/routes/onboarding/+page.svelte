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
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
	attachConsole,
	attachLogger,
	debug,
	error,
	info,
	trace,
	warn,
} from "@tauri-apps/plugin-log";

let saving = $state(false);

async function accept() {
	info("User accepted the consent dialog");
	saving = true;
	try {
		info("Saving user consent...");
		await saveConsent(true);
		info("Consent saved successfully. Navigating to main page.");
		await goto("/");
	} catch (err) {
		error(`Error saving consent: ${err}`);
	}
	saving = false;
}

async function decline() {
	error("User declined the consent dialog. Closing current window");
	await getCurrentWindow().close();
}

function handleOpenChange(open: boolean) {
	if (!open) decline();
}
</script>

  <Dialog open={true} onOpenChange={handleOpenChange}>
        <DialogContent>
                <DialogHeader>
                        <DialogTitle>Перед тем как начать</DialogTitle>
                        <DialogDescription>
                                Прочитайте предупреждение и подтвердите согласие, чтобы продолжить.
                        </DialogDescription>
                </DialogHeader>

                <div class="space-y-3 text-sm">
                        <p>
                                Это приложение автоматизирует отклики на вакансии в hh.ru.
                                <strong>Условия использования hh.ru формально запрещают такую автоматизацию</strong>,
                                и использование приложения может привести к временной или постоянной блокировке аккаунта.
                        </p>
                        <p>
                                Используйте приложение <strong>на свой риск</strong>. Рекомендуется
                                не запускать его на основном рабочем аккаунте hh.ru.
                        </p>
                        <p>
                                Нажимая «Согласен, продолжить», вы подтверждаете, что прочитали
                                это предупреждение и принимаете перечисленные риски.
                        </p>
                </div>

                <DialogFooter>
                        <Button variant="outline" onclick={decline} disabled={saving}>
                                Отказаться
                        </Button>
                        <Button onclick={accept} disabled={saving}>
                                {saving ? "Сохраняю..." : "Согласен, продолжить"}
                        </Button>
                </DialogFooter>
        </DialogContent>
  </Dialog>
