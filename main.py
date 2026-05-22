import os
import csv
import asyncio
import subprocess
import tempfile
import shutil
import logging
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message

# ==============================================================================
# CONFIGURATION
# ==============================================================================
API_ID = "YOUR_API_ID_HERE"      
API_HASH = "YOUR_API_HASH_HERE"  
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"using as Userbot  

CLIENTS_DIR = "clients"
KEYWORD_COLUMN_INDEX = 4

TEXT_EXTENSIONS = (
    ".txt", ".csv", ".tsv", ".json", ".jsonl", ".sql", ".xml", ".html", ".htm",
    ".log", ".conf", ".cfg", ".ini", ".toml", ".yaml", ".yml", ".md", ".rst",
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".php", ".rb", ".pl", ".sh", ".bash", ".ps1", ".bat", ".cmd"
)
DOCUMENT_EXTENSIONS = (
    ".pdf", ".docx", ".docm", ".dotx", ".dotm", 
    ".pptx", ".pptm", ".potx", ".potm", 
    ".xlsx", ".xlsm", ".xltx", ".xltm", ".doc", ".xls"
)
ARCHIVE_EXTENSIONS = (
    ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", 
    ".tar.gz", ".tar.bz2", ".tbz", ".tbz2", ".txz", ".xz", ".bz2"
)

SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS + DOCUMENT_EXTENSIONS + ARCHIVE_EXTENSIONS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Client("cti_hunter_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def load_keywords() -> dict:
    keywords_map = {}
    
    if not os.path.exists(CLIENTS_DIR):
        logger.warning(f"Base directory '{CLIENTS_DIR}' not found.")
        return keywords_map

    for filename in os.listdir(CLIENTS_DIR):
        
        if filename.lower().endswith(".csv"):

            client_name = os.path.splitext(filename)[0]
            csv_path = os.path.join(CLIENTS_DIR, filename)
            
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                
                next(reader, None)
                
                for row in reader:
                    if len(row) > KEYWORD_COLUMN_INDEX:
                        keyword_str = row[KEYWORD_COLUMN_INDEX].strip()
                        if keyword_str:
                            keywords_map[keyword_str] = client_name

    if not keywords_map:
        logger.warning("No keywords found in any CSV file.")
                            
    return keywords_map

async def run_command(*args) -> tuple[int, str, str]:
    """Runs a system command asynchronously to prevent blocking the bot."""
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(errors='ignore'), stderr.decode(errors='ignore')

def format_report(keyword: str, filename_hits: list, content_hits: dict, extract_dir: str) -> str:
    """Formats the results into the requested layout."""
    report = f"Target Keyword: {keyword}\n"
    report += "=" * 50 + "\n\n"

    if filename_hits:
        report += "[FILES MATCHING KEYWORD IN FILENAME]\n"
        for f in filename_hits:
            clean_path = f.replace(extract_dir, "").lstrip("/")
            report += f"- {clean_path}\n"
        report += "\n"

    if content_hits:
        for file_path, lines in content_hits.items():
            clean_path = file_path.replace(extract_dir, "").lstrip("/")
            report += f"[FILE: {clean_path}]\n"
            for line in lines:
                report += f"{line.strip()}\n"
            report += "\n"

    return report

# ==============================================================================
# MAIN BOT LOGIC
# ==============================================================================
@app.on_message(filters.group & filters.document)
async def analyze_document_handler(client: Client, message: Message):
    caption = message.caption or ""
    
    if "/analyze" not in caption.lower():
        return

    doc_name = message.document.file_name or "unknown_file"
    
    if not any(doc_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        await message.reply_text(f"❌ Unsupported file extension: {doc_name}")
        return

    # Load keywords from all client folders
    keywords_map = load_keywords()
    if not keywords_map:
        await message.reply_text(f"❌ No keywords found. Check the `{CLIENTS_DIR}` folder structure.")
        return

    status_msg = await message.reply_text("📥 Downloading archive...")

    with tempfile.TemporaryDirectory(prefix="ctihunt_") as work_dir:
        try:
            archive_path = os.path.join(work_dir, doc_name)
            await message.download(file_name=archive_path)

            extract_dir = os.path.join(work_dir, "extracted")
            results_dir = os.path.join(work_dir, "results")
            
            os.makedirs(extract_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)
            
            if doc_name.lower().endswith(ARCHIVE_EXTENSIONS):
                await status_msg.edit_text("📦 Extracting archive...")
                ret_code, stdout, stderr = await run_command("7z", "x", archive_path, f"-o{extract_dir}", "-y")
                if ret_code != 0:
                    await status_msg.edit_text(f"❌ Extraction failed. Corrupted or encrypted archive?\nError: {stderr}")
                    return
            else:
                # É um documento direto (.pdf, .docx, etc). Apenas movemos para a pasta de extração.
                await status_msg.edit_text("📄 Processing direct document...")
                shutil.copy(archive_path, os.path.join(extract_dir, doc_name))

            await status_msg.edit_text("🔍 Searching keywords...")

            # Run threat hunt for each keyword
            for keyword, client_name in keywords_map.items():
                filename_hits = []
                content_hits = defaultdict(list)

                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if keyword.lower() in file.lower():
                            filename_hits.append(os.path.join(root, file))

                ret_code, rg_out, rg_err = await run_command("rga", "-i", "-n", "-F", keyword, extract_dir)
                
                # Log de debug: se o rga der algum erro interno (ex: falta de dependências), aparecerá no seu terminal
                if rg_err:
                    logger.warning(f"RGA Alert para a keyword '{keyword}': {rg_err.strip()}")

                if rg_out:
                    for line in rg_out.splitlines():
                        if ":" in line:
                            parts = line.split(":", 2)
                            
                            if len(parts) == 3:
                                f_path, match_content = parts[0], parts[2]
                            
                            elif len(parts) == 2:
                                f_path, match_content = parts[0], parts[1]
                                
                            else:
                                continue
                                
                            content_hits[f_path].append(match_content)

                if filename_hits or content_hits:
                    report_content = format_report(keyword, filename_hits, content_hits, extract_dir)
                    report_path = os.path.join(results_dir, f"{client_name}.txt")
                    
                    # 'a' mode ensures that multiple keywords for the same client append to the same file
                    with open(report_path, "a", encoding="utf-8") as rf:
                        rf.write(report_content)

            # Check if any .txt files were created in the results directory
            generated_files = os.listdir(results_dir)
            if not generated_files:
                await status_msg.edit_text("✅ Analysis complete. No keywords found.")
                return

            # Zip the results directory
            await status_msg.edit_text("🗜️ Compacting results...")
            zip_base_path = os.path.join(work_dir, "findings")
            shutil.make_archive(zip_base_path, 'zip', results_dir)
            final_zip_path = f"{zip_base_path}.zip"

            await status_msg.edit_text("📤 Uploading findings.zip...")
            
            # Format final message
            clients_affected = [f.replace(".txt", "") for f in generated_files]
            final_text = (
                f"**Archive:** `{doc_name}`\n"
                f"**Affected Clients:** {', '.join(clients_affected)}"
            )

            await message.reply_document(document=final_zip_path, caption=final_text)
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Error processing {doc_name}: {e}")
            await status_msg.edit_text(f"❌ An error occurred during analysis: {e}")

if __name__ == "__main__":
    logger.info("CTI Hunter Bot started. Listening for documents...")
    app.run()