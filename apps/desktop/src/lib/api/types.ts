export type AuthStatus = {
	status: "authorized" | "unauthorized" | "authorizing";
};

export type AuthEvent = {
	type: "auth_changed";
	data: AuthStatus;
};

export type ServerEvent = AuthEvent;
