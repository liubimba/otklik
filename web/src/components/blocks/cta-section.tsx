import { AppleIcon, MonitorIcon, TerminalIcon } from "lucide-react";

import { Backdrop } from "@/components/ui/backdrop";
import { Button } from "@/components/ui/button";
import { Glow } from "@/components/ui/glow";
import { Magnetic } from "@/components/ui/magnetic";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { cta } from "@/lib/content";
import { links } from "@/lib/links";

const PLATFORMS = [
	{ label: "Linux", href: links.download.linux, Icon: TerminalIcon },
	{ label: "macOS", href: links.download.macos, Icon: AppleIcon },
	{ label: "Windows", href: links.download.windows, Icon: MonitorIcon },
] as const;

export function CtaSection() {
	return (
		<Section
			id="download"
			className="pb-24 md:pb-40"
			backdrop={
				<>
					<Backdrop aurora spotlight />
					{/* Тоже фон: раньше свечение лежало в children и потому обрезалось
					    по max-w-container, а рисовалось поверх кнопок. */}
					<Glow variant="below" className="opacity-70" />
				</>
			}
		>
			<SectionHeader
				id="download"
				title={cta.title}
				description={cta.description}
			/>

			<Reveal delay="delay-200" className="mt-10">
				<div className="flex flex-col items-center gap-4">
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
					<p className="max-w-[520px] text-center text-base text-pretty text-muted-foreground">
						{cta.note}
					</p>
				</div>
			</Reveal>
		</Section>
	);
}
