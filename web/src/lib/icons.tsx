import {
	AppWindowIcon,
	BriefcaseIcon,
	DatabaseIcon,
	FileUserIcon,
	GaugeIcon,
	HandIcon,
	HistoryIcon,
	KeyRoundIcon,
	ListChecksIcon,
	MessageSquareIcon,
	RefreshCwIcon,
	SearchIcon,
	ServerOffIcon,
	ShieldCheckIcon,
	SparklesIcon,
} from "lucide-react";

import type { IconKey } from "@/lib/content";

/** Мост между строковыми ключами из content.ts и компонентами lucide. */
export const sectionIcons: Record<
	IconKey,
	React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" }>
> = {
	search: SearchIcon,
	sparkles: SparklesIcon,
	messageSquare: MessageSquareIcon,
	listChecks: ListChecksIcon,
	history: HistoryIcon,
	refreshCw: RefreshCwIcon,
	database: DatabaseIcon,
	chrome: AppWindowIcon,
	serverOff: ServerOffIcon,
	keyRound: KeyRoundIcon,
	gauge: GaugeIcon,
	shieldCheck: ShieldCheckIcon,
	handRaised: HandIcon,
	fileUser: FileUserIcon,
	briefcase: BriefcaseIcon,
};
