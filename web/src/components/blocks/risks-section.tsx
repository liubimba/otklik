import { TriangleAlertIcon } from "lucide-react";

import { MascotAngry } from "@/components/ui/mascots";
import { PlainList } from "@/components/ui/plain-list";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { risks } from "@/lib/content";

export function RisksSection() {
	return (
		<Section id="risks">
			<SectionHeader
				id="risks"
				eyebrow={risks.eyebrow}
				title={risks.title}
				description={risks.description}
				mascot={<MascotAngry tone="danger" />}
			/>

			{/* Единственная сплошная плита на всю ширину окна. На пустой странице
			    заливка — самое громкое, что вообще есть, и она достаётся ровно одному
			    блоку: предупреждению о бане. destructive, а не brand: brand тоже
			    красный, они бы слиплись. */}
			<Reveal delay="delay-100" className="mt-14">
				<div className="mx-[calc(50%-50vw)] w-screen bg-destructive text-background">
					<div className="mx-auto flex max-w-container gap-4 px-4 py-10">
						<TriangleAlertIcon
							className="mt-1 size-7 shrink-0"
							aria-hidden="true"
						/>
						<div className="flex flex-col gap-3">
							<h3 className="max-w-[18ch] font-heading text-3xl text-balance md:text-4xl">
								{risks.warning.title}
							</h3>
							<p className="max-w-[70ch] text-base text-pretty">
								{risks.warning.body}
							</p>
						</div>
					</div>
				</div>
			</Reveal>

			<h3 className="mt-20 font-heading text-xl text-balance">
				{risks.mitigationsTitle}
			</h3>

			<PlainList items={risks.mitigations} columns={3} className="mt-8" />
		</Section>
	);
}
