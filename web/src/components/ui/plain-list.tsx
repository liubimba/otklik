import { Reveal } from "@/components/ui/reveal";
import { cn } from "@/lib/utils";

export type PlainItem = { title: string; body: string };

const DELAYS = ["delay-100", "delay-200", "delay-300"] as const;

/**
 * Пункты в пустоте: заголовок и текст, без коробки.
 *
 * Заменил карточки. Карточка сама по себе ничего не сообщает — она рисует рамку
 * вокруг текста и делает все пункты одинаково важными. На пустом фоне рамка ещё и
 * противоречит приёму: страница держится тем, что объекты висят в пустоте, а не
 * тем, что каждый абзац посажен в коробочку.
 */
export function PlainList({
	items,
	columns = 2,
	className,
}: {
	items: readonly PlainItem[];
	columns?: 2 | 3;
	className?: string;
}) {
	return (
		<dl
			className={cn(
				"mt-14 grid gap-x-12 gap-y-10",
				columns === 3 ? "md:grid-cols-3" : "md:grid-cols-2",
				className,
			)}
		>
			{items.map((item, index) => (
				<Reveal key={item.title} delay={DELAYS[index % DELAYS.length]}>
					<dt className="font-heading text-lg text-balance">{item.title}</dt>
					<dd className="mt-3 max-w-[50ch] text-base text-pretty text-muted-foreground">
						{item.body}
					</dd>
				</Reveal>
			))}
		</dl>
	);
}
