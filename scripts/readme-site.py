#!/usr/bin/env python3
"""Turn a README into a Zola site that uses the zola-docs theme.

The intro above the first `## ` becomes the landing page and each `## ` section becomes a page,
ported from zola-builder so README-only repos share the theme with every other site.
Env: README, OUT_DIR, BASE_URL, EXTRA (TOML lines for [extra]), GITHUB_REPOSITORY, ZOLA_VERSION.
"""
import os
import re
import shutil
import sys
from pathlib import Path


def parse_readme(readme_path):
    """Parse README.md into title, intro, and sections split by ## headings."""
    content = readme_path.read_text()
    lines = content.split("\n")

    result = {"title": "", "intro": "", "sections": []}

    i = 0
    # Find title (first # heading)
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            result["title"] = stripped[2:].strip()
            i += 1
            break
        i += 1

    # Collect intro (everything before first ##)
    intro_lines = []
    while i < len(lines):
        if lines[i].strip().startswith("## "):
            break
        intro_lines.append(lines[i])
        i += 1
    result["intro"] = "\n".join(intro_lines).strip()

    # Split by ## headings into sections
    current = None
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("## "):
            if current:
                current["content"] = "\n".join(current["_lines"]).strip()
                del current["_lines"]
                result["sections"].append(current)
            title = line.strip()[3:].strip()
            current = {"title": title, "slug": slugify(title), "_lines": []}
        elif current is not None:
            current["_lines"].append(line)
        i += 1

    if current:
        current["content"] = "\n".join(current["_lines"]).strip()
        del current["_lines"]
        result["sections"].append(current)

    return result


def slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def escape_toml(s):
    """Escape a string for use in a TOML quoted value."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def short_title(title, max_words=2):
    """Generate a short sidebar title from the first N words."""
    words = title.split()
    if len(words) <= max_words:
        return title
    return " ".join(words[:max_words])


def build_heading_map(readme_data):
    """Build a map of heading_id -> page_slug for all headings across all pages."""
    heading_map = {}

    # Headings in intro (homepage)
    for line in readme_data["intro"].split("\n"):
        m = re.match(r"^(#{2,6})\s+(.+)", line.strip())
        if m:
            heading_map[slugify(m.group(2))] = None  # None = homepage

    # Headings in each section
    for section in readme_data["sections"]:
        # The section's own title as a heading
        heading_map[section["slug"]] = section["slug"]
        # Sub-headings within the section
        for line in section["content"].split("\n"):
            m = re.match(r"^(#{2,6})\s+(.+)", line.strip())
            if m:
                heading_map[slugify(m.group(2))] = section["slug"]

    return heading_map


def fix_anchor_links(content, current_slug, heading_map):
    """Rewrite internal #anchor links to cross-page @/ links or strip broken ones."""
    def replace_link(match):
        full = match.group(0)
        text = match.group(1)
        anchor = match.group(2)

        if anchor not in heading_map:
            # Broken anchor - return just the text
            return text

        target_slug = heading_map[anchor]
        if target_slug == current_slug:
            return full  # Same page, keep as-is

        if target_slug is None:
            # Points to homepage
            return f"[{text}](/#{anchor})"

        if anchor == target_slug:
            # The section title is the page title, the template renders it without an anchor
            return f"[{text}](@/{target_slug}.md)"

        return f"[{text}](@/{target_slug}.md#{anchor})"

    return re.sub(r"\[([^\]]+)\]\(#([^)]+)\)", replace_link, content)


def toml_keys(block):
    return {m.group(1) for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", block, re.M)}


def main():
    readme = Path(os.environ["README"]).resolve()
    out = Path(os.environ["OUT_DIR"]).resolve()
    if not readme.exists():
        sys.exit(f"README not found: {readme}")
    data = parse_readme(readme)
    # Badges are for GitHub, the site has its own header
    data["intro"] = "\n".join(l for l in data["intro"].splitlines() if not l.lstrip().startswith("[![")).strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    owner, name = (repo.split("/", 1) + [""])[:2] if "/" in repo else ("", readme.parent.name)
    title = data["title"] or name

    if out.exists():
        shutil.rmtree(out)
    (out / "content").mkdir(parents=True)
    (out / "static").mkdir()

    extra = os.environ.get("EXTRA", "").strip()
    given = toml_keys(extra)
    defaults = {
        "site_name": f'"{escape_toml(title)}"',
        "author": f'"{escape_toml(owner or title)}"',
        "github": f'"https://github.com/{repo}"' if repo else None,
        "nav": '[{ name = "Docs", url = "@/_index.md" }]',
    }
    extra_lines = [f"{k} = {v}" for k, v in defaults.items() if v and k not in given]
    description = escape_toml(re.sub(r"\s+", " ", data["intro"]).strip()[:200])
    # Class based highlighting emits the z- classes the theme colours, the keys changed in Zola 0.22
    major, minor = (int(x) for x in (os.environ.get("ZOLA_VERSION") or "0.18.0").split(".")[:2])
    if (major, minor) >= (0, 22):
        highlighting = '[markdown.highlighting]\nstyle = "class"\ntheme = "github-dark"'
    else:
        highlighting = 'highlight_code = true\nhighlight_theme = "css"'
    (out / "config.toml").write_text(f"""base_url = "{os.environ.get('BASE_URL') or '/'}"
title = "{escape_toml(title)}"
description = "{description}"
theme = "zola-docs"
compile_sass = true
minify_html = true

[markdown]
{highlighting}

[extra]
{chr(10).join(extra_lines)}
{extra}
""")

    heading_map = build_heading_map(data)
    intro = fix_anchor_links(data["intro"], None, heading_map)
    (out / "content" / "_index.md").write_text(f"""+++
title = "{escape_toml(title)}"
sort_by = "weight"
template = "docs-index.html"
page_template = "docs-page.html"
+++

{intro}
""")
    for i, section in enumerate(data["sections"], start=1):
        body = fix_anchor_links(section["content"], section["slug"], heading_map)
        (out / "content" / f"{section['slug']}.md").write_text(f"""+++
title = "{escape_toml(section['title'])}"
weight = {i}

[extra]
short_title = "{escape_toml(short_title(section['title']))}"
+++

{body}
""")
    print(f"Generated {len(data['sections']) + 1} pages from {readme} into {out}")


if __name__ == "__main__":
    main()
