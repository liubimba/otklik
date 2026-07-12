import Image from "next/image";

import { Mockup, MockupFrame } from "@/components/ui/mockup";
import { cn } from "@/lib/utils";

/**
 * Скриншот приложения в рамке мокапа.
 *
 * Обе темы рендерятся в разметку, нужную выбирает CSS. Это не украшательство:
 * на сервере темы нет, и если выбирать src через useTheme(), React при
 * гидратации не перепишет разошедшийся атрибут — в светлой теме навсегда
 * останется тёмный скриншот. Один раз уже наступали.
 */
export function AppShot({
	light,
	dark,
	alt,
	priority = false,
	className,
	width = 1248,
	height = 765,
}: {
	light: string;
	dark: string;
	alt: string;
	priority?: boolean;
	className?: string;
	width?: number;
	height?: number;
}) {
	const common = {
		width,
		height,
		priority,
		sizes: "(max-width: 768px) 100vw, 640px",
	};

	return (
		<MockupFrame className={cn("mx-auto w-full", className)} size="small">
			<Mockup type="responsive">
				<Image
					{...common}
					src={light}
					alt={alt}
					className="h-auto w-full dark:hidden"
				/>
				<Image
					{...common}
					src={dark}
					alt={alt}
					className="hidden h-auto w-full dark:block"
				/>
			</Mockup>
		</MockupFrame>
	);
}
