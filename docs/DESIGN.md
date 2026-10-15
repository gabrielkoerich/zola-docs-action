# Design

Why the action and theme are built the way they are, and what each choice costs. The README covers how to use them.

## One look for many sites

| Decision | Rejected | Cost |
|---|---|---|
| The header, tagline, menu and social links are `[extra]` defaults in `theme.toml` | Each site's config repeats them, which let the menus drift apart | A site that wants another menu must override `site_nav` |
| A project's own links sit in a bar under the header | Mixing them into the top menu, which then changed from site to site | An extra row on project sites |
| Docs pages use the same `.content` article styles as blog posts | Separate docs typography, which made docs look like another site | Docs text is 20px serif, and wide tables scroll |
| On a wide screen the sidebar hangs in the left margin | A wider container on pages with a sidebar, which made the header jump when a section opened | Below 1280px the sidebar moves into the column and the text narrows |
| `scrollbar-gutter: stable` on every page | Nothing, which shifted a short page a few pixels against a long one | A gutter on pages that never scroll |
| A site's `page.html` only extends `docs-page.html` | A copy of the docs template per site, which drifted and dropped the page title | A site cannot change the docs page without overriding the whole template |

## Deploy and purge

| Decision | Rejected | Cost |
|---|---|---|
| The action deploys to Pages and then purges Cloudflare | A purge in the build job, which runs before the new site is live, so Cloudflare caches the old one again | The job needs `pages` and `id-token` permissions and the `github-pages` environment |
| One action with a `deploy` input | A separate purge action, which every site would add as a second step | `deploy` defaults to off, so an old workflow keeps uploading only |
| Purge the deployed prefix, then the hostname, then the zone | `purge_everything` on every deploy, which cleared every subdomain | Up to three API calls when a narrower purge is rejected |
| Warm the site's sitemap after the purge, with Tiered Cache and a one month Edge TTL | Letting visitors fill the cache, where the first view of each page per region waited about 150 to 300ms on GitHub Pages | A few seconds per deploy, and up to 500 requests from the runner |
| A failed or skipped purge only warns | Failing the deploy, which turns a Cloudflare outage into a failed release | A stale page can stay cached until the next deploy |
| IndexNow gets the pages whose HTML changed since the last deploy, from a hash list in the Actions cache | Every sitemap URL on each deploy, which IndexNow treats as spam, or the sitemap `lastmod`, which a docs page often lacks | An expired or evicted cache sends every page once more |
| The token is a secret in each calling repo | A token in this public repo, readable by anyone | Each repo needs the secret set once |

## Docs that follow releases

| Decision | Rejected | Cost |
|---|---|---|
| Docs build from the latest release tag | Building from `main` on every push, which published docs for unreleased features | A docs fix waits for a release, or needs a manual run with `ref=main` |
| A separate `pages.yml` | A docs job in the CI pipeline, which waited on tests, macOS runners and the release | One more workflow per project |
| The release job starts `pages.yml` with `workflow_dispatch` | Listening for the `release` event, which a release made with `GITHUB_TOKEN` never fires | The release job needs `actions: write` |

## Versions

| Decision | Rejected | Cost |
|---|---|---|
| Sites use the moving `v1` tag | Pinning a commit per site, which leaves every site to update by hand | A bad theme change reaches every site on its next deploy, so `v1` moves only after Test passes |
| The theme uses Tera 1 and supports Zola 0.18 to 0.22 | Moving to Tera 2, which Zola 0.23 needs | Sites cannot upgrade past Zola 0.22 until the theme is ported |
