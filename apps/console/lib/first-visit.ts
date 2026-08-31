const WELCOME_KEY = "loop-welcome-v2";
const DEMO_KEY = "loop-demo-done-v1";
const DEMO_COUNT_KEY = "loop-demo-count-v1";
const VISIT_COUNT_KEY = "loop-visit-count-v1";
const LAST_VISIT_KEY = "loop-last-visit-v1";
const PREV_VISIT_KEY = "loop-prev-visit-v1";
const SESSION_KEY = "loop-session-v1";
const BRIEF_DISMISS_KEY = "loop-brief-dismiss-v1";
const EXPLORE_OPEN_KEY = "loop-explore-open-v1";

function read(key: string) {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function readNum(key: string) {
  if (typeof window === "undefined") return 0;
  try {
    const v = localStorage.getItem(key);
    const n = v ? parseInt(v, 10) : 0;
    return Number.isNaN(n) ? 0 : n;
  } catch {
    return 0;
  }
}

function write(key: string) {
  try {
    localStorage.setItem(key, "1");
  } catch {
    /* private mode */
  }
}

function writeNum(key: string, n: number) {
  try {
    localStorage.setItem(key, String(n));
  } catch {
    /* private mode */
  }
}

function writeText(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode */
  }
}

function readText(key: string) {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function hasDismissedWelcome() {
  return read(WELCOME_KEY);
}

export function dismissWelcome() {
  write(WELCOME_KEY);
}

export function hasRunDemo() {
  return read(DEMO_KEY) || getDemoCount() > 0;
}

export function getDemoCount() {
  return readNum(DEMO_COUNT_KEY);
}

export function getVisitCount() {
  return readNum(VISIT_COUNT_KEY);
}

export function hoursSinceLastVisit() {
  const prev = readText(PREV_VISIT_KEY);
  if (!prev) return null;
  const t = new Date(prev).getTime();
  if (Number.isNaN(t)) return null;
  return (Date.now() - t) / 3_600_000;
}

/** Once per browser session — powers welcome-back and visit count. */
export function recordVisit() {
  if (typeof window === "undefined") return;
  try {
    if (sessionStorage.getItem(SESSION_KEY)) return;
    sessionStorage.setItem(SESSION_KEY, "1");
    sessionStorage.removeItem(BRIEF_DISMISS_KEY);

    const prev = readText(LAST_VISIT_KEY);
    if (prev) writeText(PREV_VISIT_KEY, prev);
    writeText(LAST_VISIT_KEY, new Date().toISOString());

    writeNum(VISIT_COUNT_KEY, getVisitCount() + 1);
  } catch {
    /* private mode */
  }
}

export function markDemoRun() {
  write(DEMO_KEY);
  writeNum(DEMO_COUNT_KEY, getDemoCount() + 1);
  dismissWelcome();
}

export function isFirstVisit() {
  return !hasDismissedWelcome() && !hasRunDemo();
}

export function dismissBriefSession() {
  try {
    sessionStorage.setItem(BRIEF_DISMISS_KEY, "1");
  } catch {
    /* ignore */
  }
}

export function isBriefDismissedSession() {
  if (typeof window === "undefined") return false;
  try {
    return sessionStorage.getItem(BRIEF_DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

export function getExploreOpenPreference(): boolean | null {
  const v = readText(EXPLORE_OPEN_KEY);
  if (v === "1") return true;
  if (v === "0") return false;
  return null;
}

export function setExploreOpenPreference(open: boolean) {
  writeText(EXPLORE_OPEN_KEY, open ? "1" : "0");
}
