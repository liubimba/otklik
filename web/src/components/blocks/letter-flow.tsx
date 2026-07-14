"use client";

import { FileTextIcon, RotateCcwIcon, SparklesIcon } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Laptop } from "@/components/ui/device";
import { useReveal } from "@/hooks/use-reveal";
import { type LetterVariant, letterFlow } from "@/lib/content";
import { sectionIcons } from "@/lib/icons";
import { cn } from "@/lib/utils";

/** Пауза между появлением соседних слов письма. */
const WORD_STEP_MS = 45;
/** Сколько «думает» AI, прежде чем начать переписывать. */
const THINKING_MS = 700;

type Message = { id: number; role: "user" | "ai"; text: string };

/**
 * Режем сегмент на слова, сохраняя пробелы как есть.
 *
 * Пробелы остаются обычным текстом, а не частью слова: иначе перед пунктуацией
 * следующего сегмента («…на Python» + «, и ваша задача») вылезает лишний пробел.
 * Анимируются только слова; подсветку несёт сам сегмент, поэтому фон у фразы
 * сплошной, без швов между словами.
 */
function splitWords(text: string) {
	return text.split(/(\s+)/).filter((chunk) => chunk.length > 0);
}

/** Заголовок панели внутри окна — не карточка, просто подпись. */
function PaneTitle({
	icon: Icon,
	children,
	accent = false,
}: {
	// Та же сигнатура, что у реестра в lib/icons.tsx — иначе типы не сходятся.
	icon: React.ComponentType<{
		className?: string;
		"aria-hidden"?: boolean | "true";
	}>;
	children: React.ReactNode;
	accent?: boolean;
}) {
	return (
		<h3 className="label-mono mb-3 flex items-center gap-2 text-muted-foreground">
			<Icon
				className={cn(
					"size-4",
					accent ? "text-brand" : "text-muted-foreground",
				)}
				aria-hidden
			/>
			{children}
		</h3>
	);
}

export function LetterFlow() {
	const { ref, revealed } = useReveal<HTMLDivElement>();

	const [variant, setVariant] = useState<LetterVariant>("base");
	const [messages, setMessages] = useState<Message[]>([]);
	const [pending, setPending] = useState(false);
	// Меняется на каждую перезапись: спаны письма перемонтируются по этому ключу
	// и печатаются заново.
	const [generation, setGeneration] = useState(0);

	const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
	useEffect(
		() => () => {
			if (timer.current) clearTimeout(timer.current);
		},
		[],
	);

	function ask(prompt: (typeof letterFlow.chat.prompts)[number]) {
		if (pending) return;

		setMessages((prev) => [
			...prev,
			{ id: prev.length, role: "user", text: prompt.label },
		]);
		setPending(true);

		timer.current = setTimeout(() => {
			setVariant(prompt.key);
			setGeneration((g) => g + 1);
			setMessages((prev) => [
				...prev,
				{ id: prev.length, role: "ai", text: prompt.reply },
			]);
			setPending(false);
		}, THINKING_MS);
	}

	function restart() {
		if (timer.current) clearTimeout(timer.current);
		setVariant("base");
		setGeneration((g) => g + 1);
		setMessages([]);
		setPending(false);
	}

	// Сквозной индекс слова по всему письму — им задаётся ступенчатая задержка.
	let wordIndex = 0;

	return (
		<div ref={ref} className="mt-14 md:mt-20">
			{/* Тот же корпус, что у скриншотов выше: интерактив должен читаться как
			    окно Otklik, а не как набор карточек на лендинге. Наклона нет — в
			    перекошенное окно неудобно ни читать, ни жать кнопки. */}
			<Laptop tone="none" tilt={0}>
				<div className="w-full bg-card">
					{/* Титул-бар окна */}
					<div
						aria-hidden
						className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-3"
					>
						<span className="size-2.5 rounded-full bg-muted-foreground/30" />
						<span className="size-2.5 rounded-full bg-muted-foreground/30" />
						<span className="size-2.5 rounded-full bg-muted-foreground/30" />
						<span className="label-mono mx-auto rounded-md bg-muted px-3 py-0.5 normal-case tracking-normal text-muted-foreground">
							Otklik — Backend-разработчик, Ozon
						</span>
					</div>

					{/* Источники: резюме и вакансия — рядом */}
					<div className="grid divide-y divide-border sm:grid-cols-2 sm:divide-x sm:divide-y-0">
						{letterFlow.sources.map((source) => {
							const Icon = sectionIcons[source.icon];

							return (
								<section key={source.title} className="p-5">
									<PaneTitle icon={Icon}>{source.title}</PaneTitle>
									<div className="flex flex-col gap-1.5">
										{source.lines.map((line) => (
											<span
												key={line.text}
												className={cn(
													"w-fit rounded-sm px-1.5 py-0.5 text-base",
													line.mark
														? "bg-brand/10 font-medium text-foreground ring-1 ring-brand/25"
														: "text-muted-foreground",
												)}
											>
												{line.text}
											</span>
										))}
									</div>
								</section>
							);
						})}
					</div>

					{/* Письмо */}
					<section className="border-t border-border p-5">
						<PaneTitle icon={FileTextIcon} accent>
							{letterFlow.letter.title}
						</PaneTitle>
						{/*
						 * Все слова всегда в разметке — SSR отдаёт полный текст, скринридер
						 * читает его целиком (opacity его не прячет). Печать — это лишь
						 * ступенчатая CSS-анимация. data-typed: без JS и при
						 * prefers-reduced-motion globals.css возвращает словам opacity: 1.
						 */}
						<p
							data-typed=""
							aria-live="polite"
							className={cn(
								"rounded-md bg-muted/40 p-4 text-base leading-relaxed text-pretty transition-opacity",
								pending && "opacity-40",
							)}
						>
							{letterFlow.letters[variant].map((segment, segmentIndex) => {
								const chunks = splitWords(segment.text).map((chunk) => {
									// Пробел — просто текст: он не анимируется и не подсвечивается.
									if (chunk.trim().length === 0) return chunk;

									const index = wordIndex++;
									return (
										<span
											key={`${generation}-${index}`}
											style={{ animationDelay: `${index * WORD_STEP_MS}ms` }}
											className={revealed ? "animate-appear" : "opacity-0"}
										>
											{chunk}
										</span>
									);
								});

								return segment.mark ? (
									<mark
										// biome-ignore lint/suspicious/noArrayIndexKey: сегменты письма статичны и не переупорядочиваются
										key={`${generation}-s${segmentIndex}`}
										className="rounded-sm bg-brand/10 font-medium text-foreground ring-1 ring-brand/25"
									>
										{chunks}
									</mark>
								) : (
									// biome-ignore lint/suspicious/noArrayIndexKey: то же самое — статичный список сегментов
									<Fragment key={`${generation}-s${segmentIndex}`}>
										{chunks}
									</Fragment>
								);
							})}
						</p>
					</section>

					{/* Чат с AI */}
					<section className="border-t border-border p-5">
						<PaneTitle icon={SparklesIcon} accent>
							{letterFlow.chat.title}
						</PaneTitle>

						<div className="flex flex-col gap-4">
							{messages.length === 0 ? (
								<p className="text-base text-pretty text-muted-foreground">
									{letterFlow.chat.intro}
								</p>
							) : (
								<ol aria-live="polite" className="flex flex-col gap-2">
									{messages.map((message) => (
										<li
											key={message.id}
											className={cn(
												"max-w-[85%] rounded-lg px-3 py-2 text-base text-pretty",
												message.role === "user"
													? "self-end bg-brand/10 text-foreground ring-1 ring-brand/25"
													: "self-start bg-muted text-muted-foreground",
											)}
										>
											{message.text}
										</li>
									))}
									{pending && (
										<li className="self-start rounded-lg bg-muted px-3 py-2 text-base text-muted-foreground">
											{letterFlow.chat.thinking}
										</li>
									)}
								</ol>
							)}

							<div className="flex flex-wrap gap-2">
								{letterFlow.chat.prompts.map((prompt) => (
									<Button
										key={prompt.key}
										type="button"
										variant="outline"
										size="lg"
										disabled={pending}
										onClick={() => ask(prompt)}
										className="h-11 rounded-lg px-4 text-base"
									>
										{prompt.label}
									</Button>
								))}
								{variant !== "base" && (
									<Button
										type="button"
										variant="ghost"
										size="lg"
										disabled={pending}
										onClick={restart}
										className="h-11 rounded-lg px-4 text-base"
									>
										<RotateCcwIcon className="size-4" aria-hidden />
										{letterFlow.chat.restart}
									</Button>
								)}
							</div>
						</div>
					</section>
				</div>
			</Laptop>

			<p className="mt-4 text-center text-base text-pretty text-muted-foreground">
				{letterFlow.chat.hint}
			</p>
		</div>
	);
}
