import { InfoIcon, KeyRoundIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { privacy } from "@/lib/content";
import { sectionIcons } from "@/lib/icons";

const DELAYS = ["delay-100", "delay-200", "delay-300"] as const;

export function PrivacySection() {
	return (
		<Section id="privacy" variant="muted">
			<SectionHeader
				id="privacy"
				eyebrow={privacy.eyebrow}
				title={privacy.title}
				description={privacy.description}
			/>

			<div className="mt-14 grid gap-4 md:mt-20 md:grid-cols-3">
				{privacy.cards.map((card, index) => {
					const Icon = sectionIcons[card.icon];

					return (
						<Reveal key={card.title} delay={DELAYS[index % DELAYS.length]}>
							<Card className="h-full">
								<CardHeader className="gap-3">
									<Icon className="size-5 text-brand" aria-hidden="true" />
									<h3 className="font-heading text-lg text-balance">
										{card.title}
									</h3>
								</CardHeader>
								<CardContent>
									<p className="text-base break-words text-pretty text-muted-foreground">
										{card.body}
									</p>
								</CardContent>
							</Card>
						</Reveal>
					);
				})}
			</div>

			<Reveal delay="delay-200" className="mt-4">
				<Card>
					<CardHeader className="gap-3">
						<KeyRoundIcon className="size-5 text-brand" aria-hidden="true" />
						<h3 className="font-heading text-lg text-balance">
							{privacy.key.title}
						</h3>
					</CardHeader>
					<CardContent>
						<p className="max-w-[70ch] text-base text-pretty text-muted-foreground">
							{privacy.key.body}
						</p>
					</CardContent>
				</Card>
			</Reveal>

			{/* Оговорка не должна визуально проигрывать карточкам выше — на ней держится
          достоверность всей секции. */}
			<Reveal delay="delay-300" className="mt-8">
				<Alert className="px-4 py-3">
					<InfoIcon />
					<AlertTitle className="font-heading text-base font-semibold">
						{privacy.caveat.title}
					</AlertTitle>
					<AlertDescription className="text-base text-pretty">
						{privacy.caveat.body}
					</AlertDescription>
				</Alert>
			</Reveal>
		</Section>
	);
}
