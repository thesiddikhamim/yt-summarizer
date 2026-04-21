# ai-life-skills

A collection of skills I use with Claude Code to improve my life in various ways. Designed to pair with an AI-managed Obsidian vault — the skills read from and write to the vault.

## Skills

- [`yt-summarize/`](./yt-summarize) — provide a YouTube URL or a timestamped transcription (podcast, lecture, etc.) and it writes a summary note into your vault with wikilinks to every person and concept mentioned. Asks detailed vs minimal mode on each run — detailed creates reference notes for every wikilink, minimal leaves them dangling and saves ~85% tokens.

(more coming) (daily brief, daily news)

## Install — easy mode

Open Claude Code in any directory and paste this:

> Install the ai-life-skills pack from https://github.com/thesiddikhamim/yt-summarizer. Clone the repo to `~/src/yt-summarizer`, ask me where I want the new Obsidian vault to live, create the vault folder with the full folder structure the skills expect, and symlink every skill in the repo into `~/.claude/skills/`.

Claude will:
1. Clone the repo
2. Ask where to put the vault (default: `~/ai-vault`)
3. Create the vault folder with the expected structure (see below)
4. Symlink `yt-summarize` into `~/.claude/skills/`
5. Copy the person-note template into your vault's `_Templates/` folder

Restart Claude Code so it picks up the new skills. Then run `/yt-summarize`.

> **Recommended: use a new, dedicated Obsidian vault** for these skills rather than your existing personal vault. The skills create and modify many notes/folders automatically, and keeping it separate avoids polluting notes you've written yourself.

### If you already have an Obsidian vault

You can point the skills at an existing vault if you want — tell Claude the path instead of creating a new one and it'll only create any missing folders. Just note the recommendation above about a dedicated vault.

## Install — individual skill only

If you just want one skill and already have a vault:

```bash
mkdir -p ~/src
git clone https://github.com/thesiddikhamim/yt-summarizer ~/src/yt-summarizer
ln -s ~/src/yt-summarizer/yt-summarize ~/.claude/skills/yt-summarize
```

The skills share a `templates/` folder at the repo root — leave it where it is, both skills reference it with a relative path.

## Usage

### YT-Summarize a transcription

You can provide the transcription by pasting the text directly or by providing a path to a transcription file (`.txt`, `.srt`, or `.vtt`).

```
/yt-summarize <paste transcription text here>
/yt-summarize path/to/transcript.srt
```

Summary length is proportional to the input length — a short transcription gets a short summary, a multi-hour talk gets a long one. Quotes and metadata go in the frontmatter.


```
/yt-summarize "<transcription text>" minimal
/yt-summarize "<transcription text>" detailed
```

Accepted tokens:
- **Minimal**: `minimal`, `fast`, `quick`, `--minimal`, `-m`
- **Detailed**: `detailed`, `deep`, `full`, `--detailed`, `-d`

If neither is present, the skill prompts interactively. There's no default — you either pass it or pick when asked.

**What the modes do**:
- **Detailed**: creates reference notes for every wikilink in the output, person notes for every person mentioned (researches public figures), uses the highest-quality model available
- **Minimal**: writes the summary note only, leaves wikilinks dangling, creates person notes for creators/guests only, uses Sonnet — saves ~85% on tokens for typical content

## Vault structure

```
your vault/
├── Summaries/
├── People/
├── References/
├── _Templates/
└── _Bases/             # optional, only if you use Obsidian Bases
```

Easy-mode install creates this structure for you. If you're using an existing vault, the skills prompt before creating any missing folders on first run. You can also rename any of them in the Configuration block at the top of each SKILL.md.

If you run Claude Code from outside your vault, set `VAULT_ROOT`:

```bash
export VAULT_ROOT="/path/to/vault"
```

Otherwise the skills walk up from your current directory looking for `.obsidian/`.

## Requirements

- `yt-summarize` no longer requires external CLI tools as it accepts transcriptions directly (text or `.txt`/`.srt`/`.vtt` files).

The skill checks for vault folder structure on first run and asks before creating anything.

## Tested on

- macOS 15 (Darwin 25) on Apple Silicon, Python 3.11+, Claude Code CLI
- Local transcription path assumes a Mac with MPS; the skill auto-detects CUDA / MPS / CPU and falls back to CPU on unsupported devices (slower but functional)
- ElevenLabs Scribe path works on any OS with Python + `requests`

## License

MIT.
