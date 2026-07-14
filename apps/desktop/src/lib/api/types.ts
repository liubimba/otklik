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

// Chip values accepted by GET /vacancies/all?status=. "none" is not a
// ProcessingState — it selects the vacancies that draw no badge: those with no
// application row at all, plus those still in `parsed`.
export type VacancyStatusFilter =
	| "none"
	| "letter_pending"
	| "letter_ready"
	| "letter_reviewing"
	| "letter_sending"
	| "letter_sent"
	| "error"
	| "skipped";

// A vacancy from the archive listing, with its application status joined in.
// `status: null` means no application row exists yet.
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

// A persisted past search run (backend `SearchHistoryAPISchema`). Carries the
// confirmed filter `url` plus the limits, which is everything needed to
// re-launch the run via POST /search/parse/start.
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
};

export type ApplicationDetail = {
	vacancy_id: number;
	application_id: number;
	retry_count: number;
	status: ProcessingState;
	reason: string | null;
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

// SSE events streamed from POST .../application/chat. `reply` deltas fill the
// assistant bubble; `letter` deltas stream the revised letter into the editor;
// `done` carries the new version (null for a pure answer); `error` is an
// in-band failure (the HTTP response already committed 200).
export type ChatStreamEvent =
	| { type: "reply"; delta: string }
	| { type: "letter"; delta: string }
	| { type: "done"; version: number | null }
	| { type: "error"; detail: string };

export type ApplicationsSummary = {
	needs_attention: number;
};

/**
 * Same vocabulary as the vacancies list: "all" is the whole database (what «Все
 * вакансии» shows), "latest" is the current search (what «Очередь вакансий»
 * shows — and only that).
 */
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

// Онбординг «локальная модель»: состояние Ollama на машине пользователя.
// "model_missing" — Ollama установлена и запущена, но тег модели ещё не
// стянут — отличается от "not_running", где не запущен сам демон.
export type OllamaState =
	| "not_installed"
	| "not_running"
	| "model_missing"
	| "ready";

// "weak" не блокирует установку — просто ведёт мимо загрузки модели прямо к
// облачному деплойменту, минуя замер.
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
};

export type PullProgress = {
	status: string;
	completed_bytes: number;
	total_bytes: number;
	percent: number;
	done: boolean;
};

export type BenchmarkResult = {
	passed: boolean;
	seconds: number;
	letter: string | null;
};
