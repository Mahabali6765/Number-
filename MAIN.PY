import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ CONFIG ============
BOT_TOKEN = "8648395451:AAGXWDlqQHQX9LBHlCEQemTBpNaLWOtHU2Y"          # BotFather se lo
API_URL   = "https://free.proapis.bond/num" # apna sahi URL yahan daalo
# =================================

# Ye fields kabhi show nahi honge (hide list)
HIDDEN_KEYS = {"API_Developer", "developer", "api_developer", "owner", "credit", "Today_Used"}


def extract_records(data):
    """API response me se sirf mobile records nikalta hai (nested JSON handle karta hai)"""
    records = []

    def walk(obj):
        if isinstance(obj, dict):
            # Agar is dict me 'mobile' hai to ye ek record hai
            if "mobile" in obj:
                records.append(obj)
            else:
                for v in obj.values():
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return records


def clean_address(addr):
    """Address ko sundar multi-line format me todta hai"""
    if not addr:
        return "N/A"
    # '!' se split karke clean lines banao
    parts = [p.strip() for p in str(addr).split("!") if p.strip()]
    return parts


def format_record(rec, index=None):
    """Ek single record ko sundar text me convert karta hai"""
    mobile = rec.get("mobile", "N/A")
    name   = rec.get("name", "N/A")
    fname  = rec.get("fname", "N/A")
    circle = rec.get("circle", "N/A")
    id_    = rec.get("id", "N/A")
    addr   = rec.get("address", "")

    title = f"📇 *RECORD #{index}*" if index else "📇 *RECORD*"

    text  = f"{title}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📱 *Mobile:*   `{mobile}`\n"
    text += f"👤 *Name:*     {name}\n"
    text += f"👨 *Father:*   {fname}\n"
    text += f"🌐 *Circle:*   {circle}\n"
    text += f"🆔 *ID:*       `{id_}`\n"

    # Address ko alag-alag line me dikhao
    addr_parts = clean_address(addr)
    if addr_parts:
        text += "\n🏠 *Address:*\n"
        for line in addr_parts:
            text += f"   • {line}\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 *Welcome to Number Info Bot*\n\n"
        "📌 *Kaise use karein:*\n"
        "1️⃣ Koi bhi 10-digit mobile number type karo\n"
        "2️⃣ Send dabao\n"
        "3️⃣ Bot turant poori detail de dega\n\n"
        "✅ *Kya-kya milega:*\n"
        "   • 👤 Name\n"
        "   • 👨 Father Name\n"
        "   • 🏠 Full Address\n"
        "   • 🌐 Telecom Circle\n\n"
        "🔢 *Example:* `895363****`\n\n"
        "Ab apna number bhejo 👇"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()

    if not number.isdigit() or len(number) != 10:
        await update.message.reply_text(
            "❌ *Galat input!*\n\nSirf *10 digit* ka mobile number bhejo.\n"
            "Example: `89536*****`",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text("💬 *RUKO RESULT LA RAHA HU...* ⏳", parse_mode="Markdown")

    try:
        r = requests.get(API_URL, params={"number": number}, timeout=20)

        if r.status_code != 200:
            await msg.edit_text(
                f"⚠️ *API Error*\nStatus: `{r.status_code}`\n\nTry again later.",
                parse_mode="Markdown"
            )
            return

        try:
            data = r.json()
        except ValueError:
            await msg.edit_text("❌ API ne galat response diya (JSON nahi hai).")
            return

        # Saare records nikaalo
        records = extract_records(data)

        if not records:
            await msg.edit_text(
                f"❌ *Koi record nahi mila* `{number}` ke liye.\n\n"
                "Shayad number galat hai ya database me nahi hai.",
                parse_mode="Markdown"
            )
            return

        # Header
        header = (
            f"✅ *RESULT FOUND*\n"
            f"🔎 *Searched:* `{number}`\n"
            f"📊 *Total Records:* {len(records)}\n"
        )

        # Har record format karo
        all_text = header
        for i, rec in enumerate(records, 1):
            all_text += "\n" + format_record(rec, i if len(records) > 1 else None)

        all_text += "\n🤖 *Powered by Number Info Bot*"

        # Telegram limit 4096 — bada ho to split karo
        if len(all_text) <= 4000:
            await msg.edit_text(all_text, parse_mode="Markdown")
        else:
            # Bada result — file bhej do
            await msg.edit_text(all_text[:4000], parse_mode="Markdown")
            filename = f"result_{number}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(all_text.replace("*", "").replace("`", "").replace("_", ""))
            await update.message.reply_document(
                document=open(filename, "rb"),
                filename=filename,
                caption="📄 Poora result file me bhi bhej diya."
            )

    except requests.exceptions.Timeout:
        await msg.edit_text("⏱️ *Timeout!* API slow hai, thodi der baad try karo.", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ *Error:* `{str(e)[:200]}`", parse_mode="Markdown")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    print("✅ Bot start ho gaya... Telegram pe jao aur /start bhejo")
    app.run_polling()


if __name__ == "__main__":
    main()