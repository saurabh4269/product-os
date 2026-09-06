/**
 * Gate world-data HTTP refetches: always allow the first fetch (even when the tab
 * is hidden), then skip tick-driven polls until the tab is visible again.
 */
export function shouldWorldPollFetch(pollEnabled: boolean, primed: boolean): boolean {
  return !primed || pollEnabled;
}
