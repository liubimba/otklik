import { Spotlight } from "@/components/ui/spotlight";
import { cn } from "@/lib/utils";

/**
 * Атмосферные слои секции. Серверный компонент: тема выбирается CSS, а не JS.
 *
 * Родитель обязан быть `relative` (у `Section` это так) — слой позиционируется по
 * нему и лежит под контентом, который сидит на `z-10`.
 *
 * Слои включаются по одному. Не включай все три сразу: три анимированных слоя на
 * одном экране — это уже не атмосфера, а ярмарка.
 */
export function Backdrop({
	aurora = false,
	beams = false,
	spotlight = false,
	className,
}: {
	aurora?: boolean;
	beams?: boolean;
	spotlight?: boolean;
	className?: string;
}) {
	return (
		<>
			<div
				aria-hidden="true"
				className={cn(
					"pointer-events-none absolute inset-0 z-0 overflow-hidden",
					beams && "texture-beams",
					className,
				)}
			>
				{aurora && (
					<>
						<span className="aurora-blob aurora-blob-1" />
						<span className="aurora-blob aurora-blob-2" />
						<span className="aurora-blob aurora-blob-3" />
					</>
				)}
			</div>
			{spotlight && <Spotlight />}
		</>
	);
}
