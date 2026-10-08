# South Quad dining menu bridge

Automatically retrieves the *public* [Michigan Dining South Quad menu](https://dining.umich.edu/menus-locations/dining-halls/south-quad/) using a Playwright Chromium browser, validates that the menu is dated correctly and contains real dishes, and publishes machine-readable food lists. No computer needs to be left on.

## Published results

- [Today's readable menu](docs/today.md)
- [Today's JSON with nutrition and allergen labels](docs/today.json)
- `docs/index.html` — browser-readable output

**Public raw URL** (use from ChatGPT): https://raw.githubusercontent.com/bigboyjohn238/south-quad-menu/main/docs/today.md

If the links above do not work, the first live scrape has not succeeded. **Never interpret yesterday's output as today's menu.** Each report includes a date and retrieval timestamp.

## Cloud job

GitHub Actions runs at 4:25 AM and 5:10 AM America/Detroit, plus when the workflow is uploaded or updated (push) and on manual dispatch. The job runs parser unit tests first, then fetches one day of South Quad menus in Chromium and commits the dated results in `docs/`. GitHub schedules can be delayed or skipped.

If no dishes or a mismatched date are found, the job fails rather than writing fabricated menu results. After more than 60 days of repository inactivity, GitHub may disable schedules on public repositories. Successful daily commits normally count as activity.

## Important

- The site may block GitHub-hosted browsers; see the Actions log to diagnose.
- Food availability and allergen labels can change. **Always confirm allergens with Michigan Dining staff**, particularly for severe allergies.
- No API key or login is used. The workflow accesses public menus only.
- This is independent of your laptop, but depends on GitHub Actions and the Michigan Dining page remaining accessible.
