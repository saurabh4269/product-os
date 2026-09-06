/** Sticky merge for tryGet authRequired flags across home polls. */
export function mergeAuthRequired(prev: boolean, ...flags: boolean[]): boolean {
  return prev || flags.some(Boolean);
}

/**
 * Home Connect overlay — honest glass box when protected world data is not hydrated yet
 * or the API reported authRequired. Never pretend an empty campus is authorized.
 */
export function shouldShowHomeConnectOverlay(
  adminAuthRequired: boolean,
  hasToken: boolean,
  worldHydrated: boolean
): boolean {
  if (adminAuthRequired) return true;
  if (hasToken) return false;
  return !worldHydrated;
}
