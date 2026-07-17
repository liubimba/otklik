export type AuthStatus = {
	status: "authorized" | "unauthorized" | "authorizing" | "unknown";
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

export type ErrorDomain = "model" | "submission";

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

export type VacancyStatusFilter =
	| "none"
	| "letter_pending"
	| "letter_ready"
	| "letter_reviewing"
	| "letter_sending"
	| "letter_sent"
	| "error"
	| "skipped";

export type VacancyWithStatus = Vacancy & {
	status: ProcessingState | null;
};

export type VacancyListPage = {
	items: VacancyWithStatus[];
	total: number;
};

export type SearchData = {
	search_id: string;
	parsed_vacancies: number;
	parsed_pages: number;
	status: SearchStatus;
};

export type SearchHistory = {
	id: string;
	url: string;
	max_vacancies: number;
	max_pages: number;
	status: SearchStatus;
	parsed_vacancies: number | null;
	parsed_pages: number | null;
	started_at: string | null;
	finished_at: string | null;
	error: string | null;
};

export type ApplicationData = {
	vacancy_id: number;
	application_id: number;
	status: ProcessingState;
	reason: string | null;
	error_domain: ErrorDomain | null;
};

export type ApplicationDetail = {
	vacancy_id: number;
	application_id: number;
	retry_count: number;
	status: ProcessingState;
	reason: string | null;
	error_domain: ErrorDomain | null;
	created_at: string;
	updated_at: string | null;
	latest_letter: CoverLetter | null;
	letters_count: number;
};

export type RateLimitInfo = {
	used: number;
	limit: number;
	resets_at: string;
};

export type RateLimitsBudget = {
	hourly: RateLimitInfo;
	daily: RateLimitInfo;
};

export type OrchestratorStatus = {
	reason: string | null;
	paused: boolean;
	queue_size: number;
	queue: number[];
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
	id: string;
	model: string;
	api_base?: string | null;
	has_api_key: boolean;
};

export type LLMDeploymentWrite = {
	id?: string | null;
	model: string;
	api_base?: string | null;
	api_key?: string | null;
};

export type SecretStorageMode = "keychain" | "file";
export type SecretStorage = { mode: SecretStorageMode };

export type CloudModelOption = {
	model: string;
	label: string;
	provider: string;
	key_url: string;
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

export type LLMSettingsWrite = Omit<LLMSettings, "deployments"> & {
	deployments: LLMDeploymentWrite[];
};
export type SettingsWrite = Omit<Settings, "llm"> & { llm: LLMSettingsWrite };

export type CoverLetter = {
	text: string;
	version: number;
	created_at: string;
};

export type ChatMessage = {
	id: number;
	role: "user" | "assistant";
	content: string;
	produced_version: number | null;
	created_at: string;
};

export type ChatStreamEvent =
	| { type: "reply"; delta: string }
	| { type: "letter"; delta: string }
	| { type: "done"; version: number | null }
	| { type: "error"; detail: string };

export type ApplicationsSummary = {
	needs_attention: number;
};

export type SummaryScope = "all" | "latest";

export type AICoverLetterResponse = {
	text: string;
	model_used: string;
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	was_fallback: boolean;
	cost_usd: number | null;
};

export type OllamaState =
	| "not_installed"
	| "not_running"
	| "model_missing"
	| "ready";

export type HardwareTier = "capable" | "weak";

export type HardwareSpecs = {
	ram_gb: number;
	cores: number;
	tier: HardwareTier;
};

export type SetupState = {
	hardware: HardwareSpecs;
	ollama: OllamaState;
	has_deployment: boolean;
	local_model: string;
	cloud_model: string;
	claude_available: boolean;
};

export type ClaudeCodeState = "not_installed" | "not_authed" | "ready";

export type ClaudeModelOption = {
	model: string;
	label: string;
};

export type ClaudeSetupState = {
	claude_state: ClaudeCodeState;
	default_model: string;
	model_options: ClaudeModelOption[];
};

export type LocalSetupState = {
	ollama_state: OllamaState;
	installed_models: string[];
	recommended_tag: string;
	recommended_installed: boolean;
};

export type PullProgress = {
	status: string;
	completed_bytes: number;
	total_bytes: number;
	percent: number;
	done: boolean;
};

export type BenchmarkFailureReason = "deadline" | "model_error";

export type BenchmarkResult = {
	passed: boolean;
	seconds: number;
	letter: string | null;
	failure_reason: BenchmarkFailureReason | null;
	error: string | null;
};
