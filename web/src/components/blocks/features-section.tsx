import { LetterFlow } from "@/components/blocks/letter-flow";
import { Confetti } from "@/components/ui/confetti";
import { PlainList } from "@/components/ui/plain-list";
import { Section, SectionHeader } from "@/components/ui/section";
import { features } from "@/lib/content";

export function FeaturesSection() {
	return (
		<Section
			id="features"
			backdrop={
				<Confetti
					bits={[
						{
							x: 3,
							y: 20,
							size: 16,
							shape: "diamond",
							tone: "accent-1",
							speed: 55,
						},
						{ x: 94, y: 62, size: 12, shape: "dot", tone: "brand", speed: 75 },
					]}
				/>
			}
		>
			<SectionHeader
				id="features"
				eyebrow={features.eyebrow}
				title={features.title}
				description={features.description}
			/>

			{/* Интерактив раскрывает заголовок секции: видно, что каждая фраза письма
			    выросла из резюме и описания вакансии, а не выдумана. */}
			<div className="mt-14">
				<LetterFlow />
			</div>

			<PlainList items={features.items} />
		</Section>
	);
}
