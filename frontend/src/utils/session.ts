// Session storage strategy for "Remember me" on login.
//
// Without checking "Remember me", the session lives in sessionStorage —
// gone the moment the tab/window closes, which is the safer default on a
// shared/lab computer. Checking it moves the session into localStorage,
// which is what this app always did before and survives closing the browser.
//
// Every read checks both locations (whichever currently holds it "wins"),
// since after login only one of the two is written to. Logout/expiry always
// clears both, so switching "Remember me" behavior between logins never
// leaves a stale, still-valid copy sitting in the other storage.

const TOKEN_KEY = "classpulse_token";
const ROLE_KEY = "classpulse_role";
const REMEMBERED_USERNAME_KEY = "classpulse_remembered_username";

export type Role = "student" | "teacher";

export function saveSession(token: string, role: Role, remember: boolean): void {
  const store = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  store.setItem(TOKEN_KEY, token);
  store.setItem(ROLE_KEY, role);
  other.removeItem(TOKEN_KEY);
  other.removeItem(ROLE_KEY);
}

// Used after a password change, which issues a new token — keep it in
// whichever storage already holds the session rather than assuming either.
export function updateSessionToken(token: string): void {
  if (localStorage.getItem(TOKEN_KEY)) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
}

export function getRole(): Role | null {
  return (localStorage.getItem(ROLE_KEY) ?? sessionStorage.getItem(ROLE_KEY)) as Role | null;
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(ROLE_KEY);
}

// Just the username field, independent of the session itself — so it can be
// pre-filled next time even though the actual sign-in wasn't remembered.
export function getRememberedUsername(): string {
  return localStorage.getItem(REMEMBERED_USERNAME_KEY) ?? "";
}

export function setRememberedUsername(username: string, remember: boolean): void {
  if (remember && username) {
    localStorage.setItem(REMEMBERED_USERNAME_KEY, username);
  } else {
    localStorage.removeItem(REMEMBERED_USERNAME_KEY);
  }
}
