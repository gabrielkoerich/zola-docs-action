# zola-docs-action

A GitHub Action that builds a Zola site with the shared `zola-docs` theme, the layout of gabrielkoerich.com. Every site that uses it gets the same header, menu, footer and article styles, so moving between sites feels like one website. A change here reaches each site on its next build.

[docs/DESIGN.md](docs/DESIGN.md) explains why it is built this way.

## Use it

In the site's `config.toml`:

```toml
theme = "zola-docs"
compile_sass = true

[extra]
site_name = "Orch"                                  # shows "Gabriel Koerich › Orch"
github = "https://github.com/gabrielkoerich/orch"   # the project's repo, in the project bar
stylesheet = "main.css"                             # optional, the site's own CSS on top of the theme
nav = [                                             # the project's own links, in the project bar
    { name = "Docs", url = "@/_index.md" },
    { name = "Updates", url = "@/posts/_index.md" },
]
```

The header, tagline, site menu and social links come from the theme, see [Theme defaults](#theme-defaults).

In the deploy workflow:

```yaml
jobs:
  site:
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.docs.outputs.page-url }}
    steps:
      - uses: actions/checkout@v4
      - id: docs
        uses: gabrielkoerich/zola-docs-action@v1
        with:
          path: docs
          deploy: "true"
          cloudflare-token: ${{ secrets.CF_API_TOKEN }}
```

Without `deploy`, the action only uploads the artifact, and a later job runs `actions/deploy-pages`.

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `path` | `.` | Site directory in the repo |
| `zola-version` | `0.18.0` | Zola release to build with |
| `base-url` | | Override `base_url` |
| `drafts` | `false` | Include draft pages |
| `upload` | `true` | Upload the output as a Pages artifact |
| `build-command` | | Run this in the site directory instead of `zola build`, for sites that generate pages first |
| `readme` | | Generate the site from this README instead, the intro becomes the landing page and each `## ` section a page |
| `extra` | | TOML lines for `[extra]` of a README site, such as `nav` |
| `deploy` | `false` | Deploy to GitHub Pages after the upload |
| `cloudflare-token` | | Purge the Cloudflare cache after the deploy, from the `CF_API_TOKEN` secret |
| `cloudflare-zone` | gabrielkoerich.com | Zone to purge |
| `indexnow-key` | | Ship `<key>.txt` and announce the pages changed since the last deploy to IndexNow |

Output `output-dir` holds the built site, and `page-url` the deployed URL.

The theme uses Tera 1 syntax, so it builds on Zola 0.18 to 0.22. Zola 0.23 moved to Tera 2 and rejects it.

## Theme defaults

`theme/theme.toml` sets these under `[extra]`. Zola merges them into every site's config, and a key the site sets itself wins.

| Key | Default | Shown as |
|---|---|---|
| `author` | Gabriel Koerich | First part of the header title, and the footer |
| `home_url` | https://gabrielkoerich.com | Link of the author name |
| `tagline` | Senior Engineer · AI Workflows · Solana / DeFi | Line under the title |
| `site_nav` | About, Posts, Consulting, Projects | Menu on the right of the header |
| `profile_github`, `x`, `linkedin`, `email` | the author's profiles | Icons in the header and footer |

A site sets only what is its own: `site_name`, its repo in `github` and its links in `nav`. When `site_name` is set, `nav` and `github` show in a project bar under the header, apart from the menu every site shares.

## Docs pages

`docs-page.html` renders a page with a sidebar of its section's pages, and `docs-index.html` renders the section's landing page. Both use the same article styles as a blog post.

A site whose pages use the default `page.html` points it at the theme with one line, so later theme changes reach it:

```
{% extends "docs-page.html" %}
```

Keep the docs layout and sidebar CSS out of the site's own stylesheet. A copy there overrides the theme and the text column drifts away from the header.

On a screen 1280px or wider the sidebar hangs in the left margin, so the header and text stay where every other page has them. Narrower, it sits inside the column. A long title gets a shorter sidebar label with `short_title`:

```toml
[extra]
short_title = "Channels"
```

## Docs that follow releases

For a project with releases, publish the docs from the latest release tag, so they never describe a version users cannot install yet. Put the deploy in its own `pages.yml`:

```yaml
name: Docs

on:
  workflow_dispatch:
    inputs:
      ref:
        description: Tag or branch to build, the latest release when empty
        default: ""

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page-url }}
    steps:
      - name: Pick the release to publish
        id: ref
        env:
          GH_TOKEN: ${{ github.token }}
          REF: ${{ inputs.ref }}
        run: |
          if [ -z "$REF" ]; then
            REF=$(gh release view --repo "$GITHUB_REPOSITORY" --json tagName --jq .tagName)
          fi
          echo "ref=$REF" >> "$GITHUB_OUTPUT"
      - uses: actions/checkout@v4
        with:
          ref: ${{ steps.ref.outputs.ref }}
      - id: deployment
        uses: gabrielkoerich/zola-docs-action@v1
        with:
          path: docs
          deploy: "true"
          cloudflare-token: ${{ secrets.CF_API_TOKEN }}
```

At the end of the release job, after the release exists, start it with the new tag. The job needs `actions: write`:

```yaml
      - name: Publish the docs for this release
        env:
          GH_TOKEN: ${{ github.token }}
          VERSION: ${{ needs.version.outputs.version }}
        run: gh workflow run pages.yml --repo "$GITHUB_REPOSITORY" --ref main -f ref="$VERSION"
```

A release made with `GITHUB_TOKEN` fires no `release` event for other workflows, but a `workflow_dispatch` from it does run. After a theme change, run `gh workflow run pages.yml` to rebuild the current release with the new look. To publish a docs fix before the next release, pass `-f ref=main`.

## Purge the Cloudflare cache

With `deploy` and `cloudflare-token` set, the action purges the deployed site after the deploy. A purge before the deploy lets Cloudflare cache the old site again. A site at `projects.gabrielkoerich.com/skills/` purges that prefix, and a site at the root of a hostname purges the hostname, so the rest of the zone stays cached. If Cloudflare rejects that, the action falls back to the hostname and then to the whole zone. With no token the step warns and passes, and a failed purge also only warns.

After a successful purge, the action requests every URL in the built `sitemap.xml` and the stylesheets the home page links, so the first visitor after a deploy gets a cached page. Cloudflare caches per data center, so this only reaches every region with Tiered Cache turned on (Caching → Tiered Cache, free on every plan). Each deploy purges what changed, so the cache rule can keep pages at the edge for a long Edge TTL, such as a month.

The action is public, so it cannot hold the token, and a composite action only sees the calling repo's secrets. Give each repo the secret, a token with only the Cache Purge permission:

```bash
gh secret set CF_API_TOKEN --repo owner/repo
```

## Announce changes to IndexNow

With `deploy` and `indexnow-key` set, the build writes `<key>.txt` at the site root and the action announces changed pages to IndexNow after the deploy. Bing, Yandex and the other IndexNow engines share one submission. The action hashes every `index.html`, compares the hashes with the list it kept from the last deploy in the Actions cache, and sends new, changed and deleted pages. The first deploy sends every page. Pages marked `noindex` are never sent. A failed submission warns and keeps the old list, so the next deploy sends the same pages again.

The key is public by design, so it goes in the workflow as plain text. Any 8 to 128 letters, digits or dashes work, and one key can serve every site.

## A site from a README

A repo with only a README gets a docs site with one step:

```yaml
      - uses: gabrielkoerich/zola-docs-action@v1
        with:
          readme: README.md
          base-url: https://projects.gabrielkoerich.com/skills
          deploy: "true"
          cloudflare-token: ${{ secrets.CF_API_TOKEN }}
```

The site is generated into `.zola-build`, GitHub badges are dropped and links between sections are rewritten to the new pages. `site_name` comes from the README title, `github` from the repo and `nav` defaults to a Docs link. Pass `extra` to add links, such as an npm page.

## What the theme gives a site

- `base.html` with blocks `title`, `head_extra`, `header_title`, `content`, `before_footer` and `scripts`
- The shared header and footer, and the project bar
- `docs-index.html` and `docs-page.html`, a docs layout with a sidebar of pages
- `page.html`, `index.html`, `section.html` and taxonomy pages, any of which the site can override with its own template of the same name
- Article styles for `.content`: serif body, underlined links in text, tables with the first column kept whole, heading anchors on hover
- Pages dated in the future stay hidden until a build on or after their date, `zola serve` shows them with a label
- `{{ asset(path="file.pdf") }}` shortcode for cachebusted links to static files
- Mermaid diagrams on pages that set `extra.mermaid = true`

## Preview locally

The action copies the theme in at build time, so a site keeps `themes/zola-docs` out of git:

```bash
git clone --depth 1 https://github.com/gabrielkoerich/zola-docs-action /tmp/zola-docs-action
cp -R /tmp/zola-docs-action/theme themes/zola-docs
zola serve
```

## Change the design

Edit `theme/` and push to `main`. The Test workflow builds `example/` on Zola 0.18 and 0.19. When it passes, move the `v1` tag to the new commit, and each site picks up the change on its next deploy.

Zola 0.18 rejects parentheses in a Tera `if` condition, so nest two `if` blocks instead.
