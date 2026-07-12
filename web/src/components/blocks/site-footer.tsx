import { Separator } from "@/components/ui/separator";
import { footer } from "@/lib/content";
import { links } from "@/lib/links";

const NAV = [
	{ label: "Исходный код", href: links.github },
	{ label: "Сообщить о проблеме", href: links.issues },
	{ label: "Лицензия MIT", href: links.license },
] as const;

export function SiteFooter() {
	return (
		<footer className="relative overflow-hidden bg-background px-4 pb-12 texture-grid texture-noise">
			<div className="relative z-10 mx-auto flex max-w-container flex-col gap-6">
				<Separator />

				<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
					<div className="flex flex-col gap-1">
						<span className="font-heading text-base font-extrabold">
							Otklik
						</span>
						<p className="text-base text-muted-foreground">{footer.tagline}</p>
					</div>

					<nav className="flex flex-wrap gap-x-6 gap-y-1">
						{NAV.map((item) => (
							<a
								key={item.href}
								href={item.href}
								className="-my-2 rounded-sm py-2 text-base text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							>
								{item.label}
							</a>
						))}
					</nav>
				</div>

				<p className="max-w-[70ch] text-base text-pretty text-muted-foreground">
					{footer.disclaimer}
				</p>
			</div>
		</footer>
	);
}
