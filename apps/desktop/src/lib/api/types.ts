export type AuthStatus = {
	status: "authorized" | "unauthorized" | "authorizing";
};

export type WorkFormat =
	| "remote"
	| "onsite"
	| "hybrid"
	| "traveling"
	| "unknown";

export type EmploymentType =
	| "full_time"
	| "rotational"
	| "part_time"
	| "side_job"
	| "contract"
	| "internship"
	| "unknown";

export type ProcessingState =
	| "parsed"
	| "letter_pending"
	| "letter_ready"
	| "letter_reviewing"
	| "letter_sending"
	| "letter_sent"
	| "error"
	| "skipped";

export type SearchStatus =
	| "pending"
	| "running"
	| "canceled"
	| "exited"
	| "failed"
	| "interrupted";

export type Vacancy = {
	id: number;
	title: string;
	apply_link: string;
	description: string;
	response_link: string | null;
	company_stars: string | null;
	salary: string | null;
	company_name: string | null;
	work_location: string | null;
	updated_at: string | null;
	published_at: string | null;
	work_formats: WorkFormat[];
	employment_types: EmploymentType[];
	work_experience: string | null;
};

export type SearchData = {
	search_id: string;
	parsed_vacancies: number;
	parsed_pages: number;
	status: SearchStatus;
};

export type ApplicationData = {
	vacancy_id: number;
	application_id: number;
	status: ProcessingState;
	reason: string | null;
};

export type CaptchaData = {
	vacancy_id: number;
	application_id: number;
};

export type AuthEvent = {
	type: "auth_changed";
	data: AuthStatus;
};

export type VacancyEvent = {
	type: "vacancy_new";
	data: Vacancy;
	search_id: string | null;
};

export type SearchEvent = {
	type: "search_event";
	data: SearchData;
};

export type ApplicationEvent = {
	type: "application_event";
	data: ApplicationData;
};

export type CaptchaEvent = {
	type: "captcha_event";
	data: CaptchaData;
};

export type NewFilterSession = {
	session_id: string;
};

export type FilterSessionConfirm = {
	url: string;
};

export type APIResponse = unknown;

export type FastAPIValidationIssue = {
	type: string;
	loc: (string | number)[];
	msg: string;
	input?: unknown;
};

export type APIRequestError = {
	detail?: string | FastAPIValidationIssue[];
};

export type ServerEvent =
	| AuthEvent
	| VacancyEvent
	| SearchEvent
	| ApplicationEvent
	| CaptchaEvent;

export const TERMINAL_SEARCH_STATUSES = new Set<SearchData["status"]>([
	"exited",
	"canceled",
	"failed",
	"interrupted",
]);

export type LLMDeployment = {
	model: string;
	api_key?: string | null;
	api_base?: string | null;
};

export type LLMSettings = {
	resume_text: string;
	letter_style: string;
	system_prompt?: string | null;
	deployments: LLMDeployment[];
};

export type Settings = {
	search: { max_pages: number; max_vacancies: number };
	user: { auto_submit: boolean };
	rate_limits: {
		daily_limit: number;
		hourly_limit: number;
		min_delay_ms: number;
		delay_jitter_ms: number;
	};
	llm: LLMSettings;
};
