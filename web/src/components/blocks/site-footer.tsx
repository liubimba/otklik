import { footer } from "@/lib/content";
import { links } from "@/lib/links";

const NAV = [
	{ label: "Исходный код", href: links.github },
	{ label: "Сообщить о проблеме", href: links.issues },
	{ label: "Лицензия MIT", href: links.license },
] as const;

export function SiteFooter() {
	// Сплошная заливка без фактур: подвал — фундамент страницы, а не ещё одна
	// секция. Секции чередуются сеткой/штриховкой, футер обрывает их цветом.
	return (
		<footer className="bg-footer px-4 pt-14 pb-12 text-footer-foreground">
			<div className="mx-auto flex max-w-container flex-col gap-8">
				<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
					<div className="flex flex-col gap-1">
						<span className="font-heading text-base font-extrabold">
							Otklik
						</span>
						<p className="text-base text-footer-muted">{footer.tagline}</p>
					</div>

					<nav className="flex flex-wrap gap-x-6 gap-y-1">
						{NAV.map((item) => (
							<a
								key={item.href}
								href={item.href}
								className="-my-2 rounded-sm py-2 text-base text-footer-muted underline-offset-4 transition-colors hover:text-footer-foreground hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							>
								{item.label}
							</a>
						))}
					</nav>
				</div>

				<div className="border-t border-footer-border pt-8">
					<p className="max-w-[70ch] text-base text-pretty text-footer-muted">
						{footer.disclaimer}
					</p>
				</div>
			</div>
		</footer>
	);
}
