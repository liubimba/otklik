import { InfoIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { MascotStage } from "@/components/ui/mascot-stage";
import { MascotBox } from "@/components/ui/mascots";
import { PlainList } from "@/components/ui/plain-list";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { privacy } from "@/lib/content";

export function PrivacySection() {
	return (
		<Section id="privacy">
			<SectionHeader
				id="privacy"
				eyebrow={privacy.eyebrow}
				title={privacy.title}
				description={privacy.description}
				mascot={
					<MascotStage shape="circle" tone="accent1">
						<MascotBox tone="accent2" />
					</MascotStage>
				}
			/>

			<PlainList items={[...privacy.cards, privacy.key]} />

			{/* Оговорка не должна визуально проигрывать пунктам выше — на ней держится
			    достоверность всей секции. */}
			<Reveal delay="delay-300" className="mt-12">
				<Alert className="px-4 py-3">
					<InfoIcon />
					<AlertTitle className="font-heading text-base font-extrabold">
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
