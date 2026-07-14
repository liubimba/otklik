import { AppleIcon, MonitorIcon, TerminalIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Confetti } from "@/components/ui/confetti";
import { Magnetic } from "@/components/ui/magnetic";
import { MascotStage } from "@/components/ui/mascot-stage";
import { MascotPlane } from "@/components/ui/mascots";
import { Reveal } from "@/components/ui/reveal";
import { Scribble } from "@/components/ui/scribble";
import { Section } from "@/components/ui/section";
import { cta } from "@/lib/content";
import { links } from "@/lib/links";

const PLATFORMS = [
	{ label: "Linux", href: links.download.linux, Icon: TerminalIcon },
	{ label: "macOS", href: links.download.macos, Icon: AppleIcon },
	{ label: "Windows", href: links.download.windows, Icon: MonitorIcon },
] as const;

/**
 * Единственное центрированное место на странице — и работает ровно потому, что
 * единственное. Всё остальное держит левую ось; здесь она намеренно ломается,
 * и это читается как «конец, дальше — действие».
 */
export function CtaSection() {
	return (
		<Section
			id="download"
			className="py-32 md:py-48"
			backdrop={
				<Confetti
					bits={[
						{
							x: 8,
							y: 22,
							size: 20,
							shape: "ring",
							tone: "accent-1",
							speed: 60,
						},
						{
							x: 90,
							y: 18,
							size: 14,
							shape: "diamond",
							tone: "accent-2",
							speed: 45,
						},
						{ x: 82, y: 76, size: 12, shape: "dot", tone: "brand", speed: 80 },
						{
							x: 16,
							y: 72,
							size: 16,
							shape: "diamond",
							tone: "brand",
							speed: 35,
						},
					]}
				/>
			}
		>
			<div className="flex flex-col items-center gap-10 text-center">
				{/* Запускает отклик бумажным самолётиком — единственный маскот по центру,
				    ровно там, где страница ломает левую ось и просит действия. */}
				<MascotStage shape="circle" tone="accent1" className="w-40 lg:w-48">
					<MascotPlane tone="accent2" />
				</MascotStage>

				<h2
					id="download-title"
					className="max-w-[12ch] font-heading text-balance"
				>
					{cta.title}
				</h2>
				<p className="max-w-[52ch] text-base text-pretty text-muted-foreground">
					{cta.description}
				</p>

				<Reveal delay="delay-200">
					{/* gap-12, а не gap-6: рукописный овал вокруг оговорки выходит за её
					    границы вверх, и на тесном отступе он налезал на кнопки. */}
					<div className="flex flex-col items-center gap-12">
						<div className="flex flex-wrap justify-center gap-3">
							{PLATFORMS.map(({ label, href, Icon }, index) => (
								<Magnetic key={label}>
									<Button
										asChild
										variant={index === 0 ? "default" : "glow"}
										size="lg"
										className="h-11 rounded-lg px-6 text-base"
									>
										<a href={href} className="flex items-center gap-2">
											<Icon className="size-5" aria-hidden="true" />
											{label}
										</a>
									</Button>
								</Magnetic>
							))}
						</div>

						{/* Рукописный овал — единственный «человеческий» жест на странице.
						    Обводит он именно оговорку про риски: её нельзя пролистать. */}
						<p className="max-w-[52ch] text-center text-base text-pretty text-muted-foreground">
							<Scribble>{cta.note}</Scribble>
						</p>
					</div>
				</Reveal>
			</div>
		</Section>
	);
}
