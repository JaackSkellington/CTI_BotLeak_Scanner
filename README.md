# 🕵️ CTI Hunter Bot

A Telegram bot for **Cyber Threat Intelligence** monitoring that automates keyword hunting across files, archives, and documents — mapping findings directly to clients.

---

## Overview

CTI Hunter Bot watches a Telegram group for uploaded files and, when triggered with `/analyze`, scans the content for pre-configured keywords. Each keyword is mapped to a client, and all matches are bundled into a report and sent back to the group automatically.

Built for security analysts who deal with data leaks, threat feeds, and large compressed archives on a daily basis.

---

## Features

- 📦 **Archive extraction** — supports ZIP, 7z, RAR, TAR, GZ and more via `7z`
- 📄 **Document parsing** — searches inside PDF, DOCX, XLSX, PPTX and other office formats via `rga` (ripgrep-all)
- 🔍 **Keyword matching** — filename-level and content-level search
- 🗂️ **Multi-client management** — each CSV file in `clients/` maps keywords to a client name
- 📤 **Automated reporting** — findings grouped by client and delivered as a ZIP directly in the group chat
- ⚡ **Async processing** — non-blocking execution via `asyncio` to handle heavy files without freezing the bot

---

## How It Works

1. A file is sent to a Telegram group with the caption `/analyze`
2. The bot downloads and extracts the file (if it's an archive)
3. Keywords from all CSVs in the `clients/` folder are loaded
4. `rga` (ripgrep-all) searches file contents; a filename walk catches name-level hits
5. Matches are grouped by client into `.txt` reports
6. All reports are zipped and sent back to the group

---

## Requirements

### System Dependencies

| Tool | Purpose |
|------|---------|
| `7z` (p7zip) | Archive extraction |
| `rga` (ripgrep-all) | Content search inside documents and archives |

Install on Debian/Ubuntu:
```bash
sudo apt install p7zip-full
```

For `rga`, download from the [ripgrep-all releases page](https://github.com/phiresky/ripgrep-all/releases) and place the binary in your `$PATH`.

### Python Dependencies

```
pyrogram
```

Install with:
```bash
pip install pyrogram
```

> `TgCrypto` is optional but recommended for faster Pyrogram performance:
> ```bash
> pip install tgcrypto
> ```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/cti-hunter-bot.git
cd cti-hunter-bot
```

### 2. Configure credentials

Edit the top of `bot.py` and fill in your credentials:

```python
API_ID   = "YOUR_API_ID_HERE"    # From https://my.telegram.org
API_HASH = "YOUR_API_HASH_HERE"  # From https://my.telegram.org
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # From @BotFather
```

### 3. Set up the `clients/` directory

Create one CSV file per client inside the `clients/` folder. Each file should be named after the client (e.g., `acme_corp.csv`).

The bot reads keywords from **column index 4** (the 5th column, zero-indexed). The first row is treated as a header and skipped.

Example `clients/acme_corp.csv`:
```
id,date,source,category,keyword,notes
1,2024-01-01,internal,domain,acme.com,primary domain
2,2024-01-01,internal,email,@acme.com,email domain
3,2024-01-01,internal,brand,AcmeCorp,brand name
```

> To change the keyword column, update `KEYWORD_COLUMN_INDEX` in the configuration section of `bot.py`.

### 4. Add the bot to your group

- Add the bot to a Telegram group
- Grant it permission to read and send messages

### 5. Run the bot

```bash
python bot.py
```

---

## Usage

Send any supported file to the group with `/analyze` in the caption:

```
/analyze
```

The bot will respond with status updates and, if any keywords are found, upload a `findings.zip` containing one `.txt` report per affected client.

### Supported File Types

| Category | Extensions |
|----------|-----------|
| Archives | `.zip`, `.7z`, `.rar`, `.tar`, `.gz`, `.tgz`, `.tar.bz2`, `.xz`, `.bz2` |
| Documents | `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.doc`, `.xls` and variants |
| Text/Code | `.txt`, `.csv`, `.json`, `.sql`, `.xml`, `.html`, `.log`, `.py`, `.js`, `.sh` and more |

---

## Project Structure

```
cti-hunter-bot/
├── bot.py              # Main bot logic
├── clients/            # One CSV per client with keywords
│   ├── client_a.csv
│   └── client_b.csv
└── README.md
```

---

## Report Format

Each report inside `findings.zip` follows this layout:

```
Target Keyword: acme.com
==================================================

[FILES MATCHING KEYWORD IN FILENAME]
- leaked_data/acme.com_users.txt

[FILE: leaked_data/emails.csv]
user@acme.com,hashed_password,...
```

---

## Notes

- The bot only responds to messages in **groups** that contain a supported document attachment with `/analyze` in the caption.
- Encrypted or corrupted archives will cause extraction to fail gracefully, with an error message returned to the chat.
- `rga` internal warnings (e.g., unsupported file types within an archive) are logged to the terminal but do not interrupt the analysis.

---

## License

MIT
