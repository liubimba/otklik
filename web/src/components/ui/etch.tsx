import { cn } from "@/lib/utils";

const ETCHINGS = {
	"quill-hand": { src: "/accents/quill-hand.png", ratio: 560 / 372 },
	letter: { src: "/accents/letter.png", ratio: 560 / 273 },
	manicule: { src: "/accents/manicule.png", ratio: 560 / 221 },
} as const;

export type EtchKey = keyof typeof ETCHINGS;

/**
 * Гравюра как акцентный объект — упрощённая до силуэта.
 *
 * Картинка работает МАСКОЙ, а не изображением: сам PNG — это только альфа, а цвет
 * даёт `background-color: currentColor`. Отсюда два следствия, ради которых всё и
 * затевалось: объект красится брендом и переключает тему сам, без второй копии
 * под тёмный фон, и весит копейки.
 *
 * Исходная гравюрная штриховка убрана: маски прогнаны через размытие и порог, так
 * что тонкие линии слились в сплошные пятна, а остался жирный контур с заливкой.
 * Тонкая штриховка на 140px всё равно превращалась в кашу, а весила в двадцать раз
 * больше (127 КБ против 5). Печатная машинка выброшена совсем: она детальная по
 * своей природе и в упрощении читается кляксой.
 */
export function Etch({
	name,
	className,
	width = 220,
}: {
	name: EtchKey;
	className?: string;
	/** Ширина в px; высота считается по пропорции оригинала. */
	width?: number;
}) {
	const { src, ratio } = ETCHINGS[name];

	return (
		<span
			aria-hidden="true"
			className={cn("block bg-current", className)}
			style={{
				width,
				height: width / ratio,
				maskImage: `url(${src})`,
				WebkitMaskImage: `url(${src})`,
				maskSize: "contain",
				WebkitMaskSize: "contain",
				maskRepeat: "no-repeat",
				WebkitMaskRepeat: "no-repeat",
			}}
		/>
	);
}
