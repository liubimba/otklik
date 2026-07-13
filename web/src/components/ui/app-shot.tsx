import Image from "next/image";

import { Mockup, MockupFrame } from "@/components/ui/mockup";
import { cn } from "@/lib/utils";

export type Shot = {
	light: string;
	dark: string;
	alt: string;
	/** Вайрфрейм, который держит кадр, пока грузится настоящий скриншот. */
	placeholder?: { light: string; dark: string };
};

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
	placeholder,
	priority = false,
	frame = true,
	className,
	width = 1248,
	height = 765,
	// Ширина, на которой картинка реально рисуется. Оптимизатор выбирает по ней
	// вариант из srcset, и ошибка здесь стоит резкости: с `640px` на hero,
	// который занимает всю колонку, браузер тянул 640w и растягивал вдвое.
	sizes = "(max-width: 1024px) 100vw, 620px",
}: Shot & {
	priority?: boolean;
	/**
	 * Рамка-мокап. Выключена везде, где кадр лежит на цветной плашке: рамка со
	 * скруглением и тенью поверх плоской заливки спорит сама с собой.
	 */
	frame?: boolean;
	className?: string;
	width?: number;
	height?: number;
	sizes?: string;
}) {
	// Скриншоты UI — это текст и тонкие рамки, по которым дефолтный q=75
	// заметно мажет. Вес растёт незначительно: кадры почти без градиентов.
	const common = { width, height, priority, sizes, quality: 90 };

	const shot = (
		<>
			<Placeholder src={placeholder?.light} className="dark:hidden">
				<Image {...common} src={light} alt={alt} className="h-auto w-full" />
			</Placeholder>
			<Placeholder src={placeholder?.dark} className="hidden dark:block">
				<Image {...common} src={dark} alt={alt} className="h-auto w-full" />
			</Placeholder>
		</>
	);

	if (!frame) {
		// data-slot=mockup — не украшение: по этому селектору гейт verify-page.py
		// считает кадры, сверяет тему и ловит декор, нарисованный поверх скриншота.
		return (
			<div data-slot="mockup" className={cn("w-full", className)}>
				{shot}
			</div>
		);
	}

	return (
		<MockupFrame className={cn("mx-auto w-full", className)} size="small">
			<Mockup type="responsive">{shot}</Mockup>
		</MockupFrame>
	);
}

/**
 * Вайрфрейм-подложка. `next/image` рисует прозрачный <img> до загрузки и сам
 * резервирует место по width/height, поэтому фон видно ровно до того момента,
 * как непрозрачный PNG его перекроет. Никакого JS и состояния загрузки.
 */
function Placeholder({
	src,
	className,
	children,
}: {
	src?: string;
	className?: string;
	children: React.ReactNode;
}) {
	return (
		<div
			className={cn("w-full bg-cover bg-center", className)}
			style={src ? { backgroundImage: `url(${src})` } : undefined}
		>
			{children}
		</div>
	);
}
