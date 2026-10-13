# zola-docs-action

A GitHub Action that builds a Zola site with the shared `zola-docs` theme, the layout of gabrielkoerich.com. Every site that uses it gets the same CSS, header, nav and footer. A change here reaches each site on its next build.

## Use it

In the site's `config.toml`:

```toml
theme = "zola-docs"
compile_sass = true

[extra]
author = "Gabriel Koerich"
site_name = "Orch"                     # optional, shows "Gabriel Koerich › Orch"
home_url = "https://gabrielkoerich.com"
tagline = "Senior Engineer · AI Workflows · Solana / DeFi"
github = "https://github.com/gabrielkoerich"
linkedin = "https://linkedin.com/in/gabrielkoerich"
email = "gabriel@gabrielkoerich.com"
stylesheet = "main.css"                # optional, the site's own CSS on top of the theme
nav = [
    { name = "Posts", url = "https://gabrielkoerich.com/posts/" },
    { name = "Docs", url = "@/docs/_index.md" },
]
```

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
| `extra` | | TOML lines for `[extra]` of a README site, such as `author`, `home_url`, `tagline` or `nav` |
| `deploy` | `false` | Deploy to GitHub Pages after the upload |
| `cloudflare-token` | | Purge the Cloudflare cache after the deploy, from the `CF_API_TOKEN` secret |
| `cloudflare-zone` | gabrielkoerich.com | Zone to purge |

Output `output-dir` holds the built site, and `page-url` the deployed URL.

The theme uses Tera 1 syntax, so it builds on Zola 0.18 to 0.22. Zola 0.23 moved to Tera 2 and rejects it.

## Purge the Cloudflare cache

With `deploy` and `cloudflare-token` set, the action purges the deployed site after the deploy. A purge before the deploy lets Cloudflare cache the old site again. A site at `projects.gabrielkoerich.com/orch/` purges that prefix, and a site at the root of a hostname purges the hostname, so the rest of the zone stays cached. If Cloudflare rejects that, the action falls back to the hostname and then to the whole zone. With no token the step warns and passes, and a failed purge also only warns.

The action is public, so it cannot hold the token, and a composite action only sees the calling repo's secrets. Set the secret on each repo from passbox:

```bash
passbox exec --stdin cf/purge-token -- gh secret set CF_API_TOKEN --repo gabrielkoerich/<repo>
```

## A site from a README

A repo with only a README gets a docs site with one step, the successor to zola-builder:

```yaml
      - uses: gabrielkoerich/zola-docs-action@v1
        with:
          readme: README.md
          base-url: https://projects.gabrielkoerich.com/skills
          extra: |
            author = "Gabriel Koerich"
            home_url = "https://gabrielkoerich.com"
```

The site is generated into `.zola-build`, GitHub badges are dropped and links between sections are rewritten to the new pages.

## What the theme gives a site

- `base.html` with blocks `title`, `head_extra`, `header_title`, `content`, `before_footer` and `scripts`
- `docs-index.html` and `docs-page.html`, a docs layout with a sidebar of pages
- `page.html`, `index.html`, `section.html` and taxonomy pages, any of which the site can override with its own template of the same name
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

Edit `theme/`, push, and the Test workflow builds `example/` on each supported Zola version. Sites pick up the change on their next deploy.
