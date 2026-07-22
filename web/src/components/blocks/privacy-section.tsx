import { MascotStage } from "@/components/ui/mascot-stage";
import { MascotBox } from "@/components/ui/mascots";
import { PlainList } from "@/components/ui/plain-list";
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
		</Section>
	);
}
