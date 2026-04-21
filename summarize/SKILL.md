---
name: summarize
description: Summarize any content (YouTube video, article, podcast, lecture, etc.) by providing a timestamped transcription. Produces a rich Obsidian note with section-by-section breakdowns, wikilinks to all technical concepts and people, and reference notes for every linked term.
user_invocable: true
---

# Summarize

Universal content summarizer. Takes a timestamped transcription — from YouTube, podcast, lecture, or any spoken-word content — and produces a rich, interlinked Obsidian summary note with reference notes for every concept mentioned.

## Requirements

**Vault structure** — the skill expects these folders inside your Obsidian vault. Folder names are the defaults; override them in the Configuration block below if your vault uses different names.

| Folder | Purpose |
|---|---|
| `Summaries/` | Where summary notes land |
| `References/` | Concept / company / product / place notes |
| `People/` | Person notes (creators, guests, mentioned people) |
| `_Templates/` | Note templates — skill installs `new person template.md` here on first run |
| `_Bases/` (optional) | Obsidian Bases — only needed if you use the Bases plugin |

**CLI tools** — install these before first use, or let Step 0 walk you through it:

| Tool | Purpose | Install |
|---|---|---|
| `youtube-transcript-api` | Fetch YouTube transcriptions | `pip install youtube-transcript-api` |
| `python3` | Run the transcription script | N/A (Pre-installed on macOS) |


## Configuration

The skill reads these variables at runtime. Override any of them via environment variables, or edit the defaults here:

```
VAULT_ROOT     = $VAULT_ROOT        # auto-detected if not set (see Step 0a)
SUMMARIES_DIR  = Summaries
REFERENCES_DIR = References
PEOPLE_DIR     = People
TEMPLATES_DIR  = _Templates
BASES_DIR      = _Bases
```

All paths below are relative to `$VAULT_ROOT`.

## Trigger

When the user provides a transcription to summarize (via pasting text or providing a `.txt`, `.srt`, or `.vtt` file).

## Inputs

- **Source**: Transcription text (pasted or from a `.txt`, `.srt`, or `.vtt` file)
- **Metadata**: Title, Channel/Author, Source URL (if available)
- **Audience** (optional): defaults to "general reader." User may specify (e.g. "high school student", "expert", "5-year-old")
- **Depth** (optional): defaults to "full." User may request "tldr only", "section-by-section", or "deep dive"

## Step 0: Bootstrap check (first run)

Before doing any work, verify the environment is ready. **Skip any check that already passes** — only prompt the user when something is actually missing. Do not re-run Step 0 on subsequent invocations if the initial setup succeeded; you can tell it already ran if `$VAULT_ROOT` resolves and the required folders + tools are present.

### 0a. Resolve the vault root

```bash
vault=""
if [ -n "$VAULT_ROOT" ]; then
  vault="$VAULT_ROOT"
else
  dir="$PWD"
  while [ "$dir" != "/" ]; do
    if [ -d "$dir/.obsidian" ]; then vault="$dir"; break; fi
    dir="$(dirname "$dir")"
  done
fi
echo "Vault: ${vault:-NOT FOUND}"
```

If no vault is found, ask the user:

> **What's the absolute path to your Obsidian vault?**
> Recommended: use a **new, dedicated Obsidian vault** for this skill — not your existing personal vault. The skill creates and modifies many notes and folders, and a clean vault avoids polluting your existing notes. If you don't have one yet, create an empty folder, open it in Obsidian (File → Open vault as folder), and paste that path here.

After they answer, validate that `<answer>/.obsidian/` exists before using it — if not, warn that the path doesn't look like an Obsidian vault (they may need to open it in Obsidian first) and ask them to confirm or re-enter. Use the validated answer as `$VAULT_ROOT` for the session (and suggest they set it permanently in their shell profile).

### 0b. Check required folders

```bash
for d in "$SUMMARIES_DIR" "$REFERENCES_DIR" "$PEOPLE_DIR" "$TEMPLATES_DIR"; do
  [ -d "$VAULT_ROOT/$d" ] || echo "MISSING: $d"
done
```

For each missing folder, ask the user: **"Create `<folder>` in your vault? [y/N]"** — if yes, `mkdir -p "$VAULT_ROOT/<folder>"`.

### 0c. Check required CLI tools

```bash
if ! python3 -c "import youtube_transcript_api" 2>/dev/null; then
  echo "MISSING: youtube-transcript-api"
fi
```

If missing, ask the user: **"Install `youtube-transcript-api` via pip? [y/N]"** — if yes, `pip3 install youtube-transcript-api`.

### 0d. Install the person template if missing

The skill ships two person templates in the repo's `templates/` folder (shared with `summarize-call`):

- **`new person template.md`** — full version with Dataview callouts (current age, total hours talked) and Obsidian Bases embeds (`posts.base`, `books.base`, `meetings.base`). Requires the Dataview plugin and Obsidian Bases.
- **`new person template (minimal).md`** — stripped version. Just frontmatter, a `> [!info]` summary callout, and an `## updates` section. Works in any vault.

If `$VAULT_ROOT/$TEMPLATES_DIR/new person template.md` already exists, leave it alone — the user may have their own customized version.

Otherwise, ask the user which version to install:

> **Install person template — which version?**
> 1. **Minimal** (default, works in any vault)
> 2. **Full** (requires Dataview plugin + Obsidian Bases)

Then copy the chosen template into the user's `_Templates/` folder:

```bash
skill_dir="$(dirname "$0")"   # or wherever this SKILL.md lives
target="$VAULT_ROOT/$TEMPLATES_DIR/new person template.md"

if [ ! -f "$target" ]; then
  # Use the user's choice — default to minimal
  src="$skill_dir/../templates/new person template (minimal).md"
  # if user picked full: src="$skill_dir/../templates/new person template.md"
  cp "$src" "$target"
fi
```

Note: whichever version gets installed lands at `_Templates/new person template.md` (no `(minimal)` suffix) so the skill's later references work uniformly.

Once Step 0 passes, proceed to Step 0.5.

## Step 0.5: Determine depth mode

Before extraction, establish which depth the user wants:

1. **Scan the invocation first.** If the user's request already specifies a mode, use it and skip the prompt:
   - Words like `minimal`, `fast`, `quick`, `--minimal`, `-m` → minimal mode
   - Words like `detailed`, `deep`, `full`, `--detailed`, `-d` → detailed mode
2. **Otherwise, prompt.** No default — if unspecified, ask every time:

> **Depth?**
> 1. **Detailed** (best results) — full reference notes for every wikilinked concept, person notes for every mentioned person, parallel highest-available-model subagents per section, base updates
> 2. **Minimal** (fast) — summary note only, wikilinks left dangling, person notes for creators/guests only, Sonnet summary

This keeps interactive runs explicit while letting scheduled tasks / cron / `/loop` pass the mode in the invocation (e.g. `/summarize <url> minimal`) without blocking on input.

The chosen mode determines which steps run:

| Step | Detailed | Minimal |
|---|---|---|
| 1 Extract text | ✓ | ✓ |
| 1b Save transcript | ✓ | ✓ |
| 2 Output structure | ✓ | ✓ |
| 3a Depth from word count | ✓ | ✓ |
| 3b Parallel subagents | ✓ (>3000 words, highest available model) | ✓ (>3000 words, Sonnet) |
| 4 Assemble summary | ✓ | ✓ (skip `## People Mentioned` section) |
| 5 Reference notes (concepts) | ✓ | ✗ — wikilinks left dangling |
| 5 Person notes | ✓ (all mentioned) | ✓ (creators/guests only — those in `people` frontmatter) |
| 5c Dangling-link audit | ✓ | ✗ |
| 6 Bases update | ✓ (if bases exist) | ✗ |

For book chapter-by-chapter depth (Step 1 book section), detailed mode gets the full 300-600 words per chapter; minimal mode gets a flatter single summary regardless of chapter count.

## Step 1: Accept transcription and metadata

Accept the transcription or a YouTube URL from the user. This can be provided in four ways:
1. **YouTube URL**: The user provides a link starting with `https://youtube.com` or `https://youtu.be`.
2. **Direct Paste**: The user pastes the full transcription text into the chat.
3. **File Path**: The user provides a path to a `.txt`, `.srt`, or `.vtt` file.
4. **Environment Variable**: For automated runs, the transcription might be passed via an environment variable or piping.

If a **YouTube URL** is provided:
1. Run the transcription script: `python3 transcription.py "<url>"` (script located in the repo root).
2. Use the output as the transcription text.
3. If an error occurs (e.g., "Error: ..."), inform the user and ask for the transcription manually.

If the user provides a **file path**, read the file content immediately. For `.srt` and `.vtt` files, maintain the timestamps as they are essential for the structured summary and referencing.

Also gather metadata (title, author/channel, source URL) from the user. If metadata is missing, ask the user to provide it to ensure the resulting vault note is properly named and linked. For YouTube URLs, the script provides the text, but the user may still need to confirm the title and channel name if they want specific folder nesting.


## Step 1b: Save transcript

Save the provided transcription as a permanent vault note.

**Location:** Same folder as the summary note, with ` Transcript` appended to the filename.

**Format:**
```markdown
---
date: YYYY-MM-DD
recording: "<source URL>"
meeting: "[[<Summary Note Title>]]"
unread: true
---

[Full timestamped transcript text, one line per segment]
```

**Link from summary:** Add `transcript: "[[<Title> Transcript]]"` to the summary note's frontmatter.


**Location:** Same folder as the summary note, with ` Transcript` appended to the filename.

**Format:**
```markdown
---
date: YYYY-MM-DD
duration: <seconds>
recording: "<source URL>"
meeting: "[[<Summary Note Title>]]"
unread: true
---

[Full timestamped transcript text, one line per segment]
```

**Link from summary:** Add `transcript: "[[<Title> Transcript]]"` to the summary note's frontmatter.

This step happens immediately after text extraction (Step 1) and before output structure planning (Step 2). The transcript is the raw source material — always preserve it.

## Step 2: Determine output structure

Based on content type, choose the appropriate format:

| Content type | Location | Frontmatter tags | Extra fields |
|---|---|---|---|
| YouTube video | `08 Summaries/<Channel>/Summaries/<Title>.md` | `youtube` | `recording`, `views`, `creator`, `people`, `guest`, `hosts`, `guests`, `duration`, `uploaded`, `transcript` |
| Article / blog | `08 Summaries/<Title>.md` | `article` | `creator`, `source` (URL), `published` |
| Whitepaper / PDF | `08 Summaries/<Title>.md` | `paper` | `authors`, `affiliations`, `source` (wikilink to PDF if in vault, or URL), `published` |
| EPUB / book | `08 Summaries/<Title>.md` | `book` | `creator` (author wikilink), `published` (year), `isbn`, `source` (wikilink to epub if in vault) |
| Podcast episode | `08 Summaries/<Show>/Summaries/<Title>.md` | `podcast` | `recording`, `people`, `guest`, `hosts`, `guests`, `duration`, `transcript` |
| Lecture / talk | `08 Summaries/<Title>.md` | `lecture` | `creator`, `recording` (if URL), `transcript` |

**All notes** get: `created`, `updated`, `date`, `summary`, `categories: ["[[posts.base]]"]`, `unread: true`

If a channel/show folder is needed, check if it already exists before creating.

## Step 3: Analyze structure, determine depth, and plan sections

Read the full extracted text. Identify the natural sections/chapters/topics.

### 3a. Determine summary depth from source length

Summary length must be **proportional** to the source material. A 10-minute video and a 3-hour documentary should not produce the same size summary. Use the source word count to determine the target summary word count:

| Source word count | Source examples | Target summary words | Sections | TLDR |
|---|---|---|---|---|
| <1,500 | 5-min video, short article | 200–400 | 1–2 | 2 sentences |
| 1,500–5,000 | 10–20 min video, blog post, short paper | 500–1,200 | 3–5 | 3 sentences |
| 5,000–15,000 | 30–60 min video, long article, whitepaper | 1,500–3,000 | 5–8 | 3–4 sentences |
| 15,000–40,000 | 1–3 hr video/podcast, long paper | 3,000–6,000 | 8–15 | 4–5 sentences |
| 40,000–80,000 | Short book, multi-hour series | 5,000–10,000 | 15–25 | 5 sentences |
| 80,000+ | Full book (200+ pages) | 8,000–15,000 | 20–40 | 5 sentences |

**The ratio is roughly 1:5 to 1:10** — a 10,000-word source should produce ~1,500–2,500 words of summary. Denser/more technical content skews toward the higher end; conversational/repetitive content skews lower.

**For videos/podcasts**, estimate source words from duration: ~150 words/minute for conversational, ~120 words/minute for interviews with pauses, ~170 words/minute for scripted/narrated content. Or just use the actual transcript word count.

**Per-section depth**: each section's word budget should be proportional to its share of the source material. A section covering 20% of the transcript gets ~20% of the summary word budget. Adjust up for particularly dense/important sections, down for filler/repetitive ones.

### 3b. Plan sections and dispatch

**For long content (>3000 source words):** dispatch parallel subagents (see Model usage table for which model) — one per section — to summarize simultaneously. Each subagent gets:
- The section text
- The audience level
- A **specific word count target** (calculated from 3a above)
- Instructions to use `[[wikilinks]]` for every technical concept, person, place, company, and notable noun

**For short content (<3000 source words):** summarize directly without subagents.

**Model choice**: detailed mode uses the highest available model (Opus if the user has access, else Sonnet); minimal mode always uses Sonnet. Never Haiku.

## Step 4: Assemble the summary note

### Structure

```markdown
---
[frontmatter per Step 2]
---

[embed if applicable: ![[file.pdf]], ```vid URL```, etc.]

> [!tldr]
> [Overview — sentence count per Step 3a depth table. What is it about, who made it, what are the key takeaways?]

## [Section 1 Title]

[Summary paragraphs with [[wikilinks]] to all concepts, people, places, companies, products]

## [Section 2 Title]

[...]

## People Mentioned
- [[Person Name]] — brief context of who they are and their role in this content
```

### Formatting rules

1. **No `# Title` heading** — filename is the title
2. **Never repeat frontmatter in the body** — if it's in metadata, don't write it again
3. **`> [!tldr]`** for the overview, not `## Summary`
4. **`> [!quote]`** callouts for notable quotes (with speaker wikilink and source location if available)
5. **Wikilink EVERYTHING** — people, places, companies, concepts, technical terms, **book/film/show titles**, even if no note exists yet
6. **Use actual Japanese/Chinese characters** for non-English words, not romanization
7. **Timestamps** on topic headings and quotes when available (YouTube, podcasts)
8. **`people` field**: only people who created/appeared in the content. Mentioned people go in `## People Mentioned`

### Audience adaptation

- **High school / college student**: plain language, analogies, explain jargon inline before first wikilink use
- **General reader**: balanced — explain key terms but don't over-simplify
- **Expert**: technical language fine, focus on novel contributions and critiques

## Step 5: Create reference notes (one layer deep)

**This is the most important step. Every wikilink MUST resolve to a note. No dangling links.**

### 5a. Extract and audit all wikilinks

After the summary note is fully assembled, extract every unique wikilink programmatically:

The regex excludes `|` (alias), `#` (heading ref), and `^` (block ref) so `[[Target|Alias]]`, `[[Page#Heading]]`, and `[[Page^block]]` all resolve to the canonical note name (`Target` / `Page`):
```bash
grep -oE '\[\[[^]|#^]+' "<summary_note_path>" | sed 's/\[\[//' | sort -u
```

Then check which ones are missing:

```bash
for term in <each extracted term>; do
  found=$(find "$VAULT_ROOT" -name "$term.md" \
    -not -path "*/.Trash/*" -not -path "*/Clippings/*" 2>/dev/null | head -1)
  if [ -z "$found" ]; then echo "MISSING: $term"; fi
done
```

**Do NOT skip this step. Do NOT estimate from memory which notes exist.** Always run the audit.

### 5b. Create missing notes

#### Technical concepts, companies, products, places
Create in `07 References/<Term>.md`:

```markdown
---
created: YYYY-MM-DDT00:00
updated: YYYY-MM-DDT00:00
type: reference
unread: true
---

[2-4 sentence plain-language explanation. Use [[wikilinks]] to cross-reference related concepts.]
```

#### People
Create in `$PEOPLE_DIR/<Full Name>.md` using the person template at `$VAULT_ROOT/$TEMPLATES_DIR/new person template.md` (installed by Step 0d). Conventions:

- **Public figures**: research and write a rich bio (birthday, career, links, key facts). The `> [!info]` callout should be a substantive snapshot — life story, mission, current focus — not a stub.
- **Private individuals**: minimal note with only what's known from the content. The note will grow naturally over time.
- **`> [!note] current age` callout** (from template): keep it if `birthday` is known or can be estimated. If estimated, append `(estimated)` to the callout text — but `birthday` in frontmatter must stay a pure YAML date (e.g. `2001-01-01`), never text.
- **`> [!abstract] total hours talked` callout** (from template): ONLY keep this if the person has had real 1-on-1 calls/meetings with the vault owner (i.e. they appear in meeting notes). Delete the callout for people discovered through summarizing videos, articles, books, or podcasts — those people will never have meeting entries, so the callout would always show 0h.
- **No `# Title` heading** — Obsidian shows the filename as the title.
- **`unread: true`** in frontmatter on every new or modified note.

#### Dispatch in parallel
For large numbers of missing notes (>10), use parallel subagents (highest available model) in batches of ~20-25 notes each. Each subagent creates the notes and returns confirmation.

### 5c. Verify — no dangling links

After all notes are created, re-run the audit from 5a to confirm zero missing notes. If any remain (e.g. a subagent failed or skipped one), create them manually. **The summary is not done until this verification passes.**

## Step 6: Update bases (optional — skip if not using Obsidian Bases)

This step only applies if `$VAULT_ROOT/$BASES_DIR/posts.base` exists. If it doesn't, skip Step 6 entirely.

```bash
[ -f "$VAULT_ROOT/$BASES_DIR/posts.base" ] || echo "No posts.base — skipping Step 6"
```

If it does exist:
- **`posts.base`**: if new people appeared as creators/guests, add named views for them using the YAML block below, then embed them in their person notes (in a `## episodes` or `## videos` section) via `![[posts.base#Person Name]]`.
- If a new channel/show folder was created, add a channel-specific view to `posts.base` the same way.

Named view YAML block to append under the `views:` list:
```yaml
  - type: table
    name: "Person Name"
    filters:
      and:
        - recording != null
        - people.contains(link("Person Name"))
    order:
      - date
      - views
      - file.name
      - summary
    sort:
      - property: date
        direction: DESC
```

## Step 6: Update bases (optional)
# (Logic continues from Step 6)

## Model usage

| Task | Detailed | Minimal |
|------|----------|---------|
| Content extraction | Provided by user | Provided by user |
| Section summarization | Highest available (Opus if accessible, else Sonnet) | **Sonnet** |
| Reference note creation | Highest available | (skipped) |
| Person note creation | Highest available | **Sonnet** (creators/guests only) |
| **NEVER** | **Haiku** | **Haiku** |

## Key rules

1. **Wikilink everything** — every concept, person, company, place, and **book/film/show title** gets a `[[wikilink]]`
2. **One layer deep** — create reference/person notes for EVERY wikilinked term that doesn't already have a note
3. **No `# Title` headings** — Obsidian shows filename as title
4. **Never repeat frontmatter in body** — frontmatter is metadata, body is content
5. **Set `unread: true`** on every note created or modified
6. **Parallel Opus subagents** for long content — one per section for summaries, batches of ~20 for reference notes
7. **Audience-appropriate language** — match the user's requested level
8. **Always embed/link the source** — PDF embed, vid embed, or source URL in frontmatter
9. **`> [!tldr]`** is mandatory — every summary starts with a concise overview callout
10. **Person note `## updates` links to the content note**
