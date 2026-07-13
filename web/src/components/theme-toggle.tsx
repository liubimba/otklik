"use client";

import { MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
	const { resolvedTheme, setTheme } = useTheme();

	return (
		<Button
			variant="ghost"
			size="icon-lg"
			aria-label="Переключить тему"
			onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
		>
			{/* Иконка выбирается CSS, а не состоянием: на сервере тема неизвестна,
          и любой рендер по ней даёт hydration mismatch и мигание при загрузке. */}
			<MoonIcon className="size-5 dark:hidden" />
			<SunIcon className="hidden size-5 dark:block" />
		</Button>
	);
}
