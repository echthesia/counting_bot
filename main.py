import numexpr as ne
import logging
import string
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters, PicklePersistence
import dotenv
import os
from telegram.constants import ParseMode
import unicodedata
import icu

PUNCTUATION_FILTER = ''.join(c for c in string.punctuation if c not in '-.')

def parse_number(text: str) -> float | None:
    """Parse number string using multiple numeral systems."""
    # Locales with different numeral systems
    locales = ["en-US@numbers=adlm", "en-US@numbers=ahom", "en-US@numbers=arab", "en-US@numbers=arabext", "en-US@numbers=armn", "en-US@numbers=armnlow", "en-US@numbers=bali", "en-US@numbers=beng", "en-US@numbers=bhks", "en-US@numbers=brah", "en-US@numbers=cakm", "en-US@numbers=cham", "en-US@numbers=cyrl", "en-US@numbers=deva", "en-US@numbers=diak", "en-US@numbers=ethi", "en-US@numbers=finance", "en-US@numbers=fullwide", "en-US@numbers=gara", "en-US@numbers=geor", "en-US@numbers=gong", "en-US@numbers=gonm", "en-US@numbers=grek", "en-US@numbers=greklow", "en-US@numbers=gujr", "en-US@numbers=gukh", "en-US@numbers=guru", "en-US@numbers=hanidays", "en-US@numbers=hanidec", "en-US@numbers=hans", "en-US@numbers=hansfin", "en-US@numbers=hant", "en-US@numbers=hantfin", "en-US@numbers=hebr", "en-US@numbers=hmng", "en-US@numbers=hmnp", "en-US@numbers=java", "en-US@numbers=jpan", "en-US@numbers=jpanfin", "en-US@numbers=jpanyear", "en-US@numbers=kali", "en-US@numbers=kawi", "en-US@numbers=khmr", "en-US@numbers=knda", "en-US@numbers=krai", "en-US@numbers=lana", "en-US@numbers=lanatham", "en-US@numbers=laoo", "en-US@numbers=latn", "en-US@numbers=lepc", "en-US@numbers=limb", "en-US@numbers=mathbold", "en-US@numbers=mathdbl", "en-US@numbers=mathmono", "en-US@numbers=mathsanb", "en-US@numbers=mathsans", "en-US@numbers=mlym", "en-US@numbers=modi", "en-US@numbers=mong", "en-US@numbers=mroo", "en-US@numbers=mtei", "en-US@numbers=mymr", "en-US@numbers=mymrepka", "en-US@numbers=mymrpao", "en-US@numbers=mymrshan", "en-US@numbers=mymrtlng", "en-US@numbers=nagm", "en-US@numbers=native", "en-US@numbers=newa", "en-US@numbers=nkoo", "en-US@numbers=olck", "en-US@numbers=onao", "en-US@numbers=orya", "en-US@numbers=osma", "en-US@numbers=outlined", "en-US@numbers=rohg", "en-US@numbers=roman", "en-US@numbers=romanlow", "en-US@numbers=saur", "en-US@numbers=segment", "en-US@numbers=shrd", "en-US@numbers=sind", "en-US@numbers=sinh", "en-US@numbers=sora", "en-US@numbers=sund", "en-US@numbers=sunu", "en-US@numbers=takr", "en-US@numbers=talu", "en-US@numbers=taml", "en-US@numbers=tamldec", "en-US@numbers=tnsa", "en-US@numbers=telu", "en-US@numbers=thai", "en-US@numbers=tirh", "en-US@numbers=tibt", "en-US@numbers=vaii", "en-US@numbers=wara", "en-US@numbers=wcho"]
    
    # Try direct float conversion first
    try:
        return float(text)
    except ValueError:
        pass
    
    # Check for mixed numeral systems
    script = None
    for char in text:
        if script is None:
            script = icu.Script.getScript(char)
        elif icu.Script.getScript(char) != script:
            return None
        else:
            continue
        

    # Try ICU parsing with different locales
    for locale in locales:
        try:
            num_fmt = icu.NumberFormat.createInstance(icu.Locale(locale))
            parsed = num_fmt.parse(text).getDouble()
            if parsed is not None:
                return float(parsed)
        except Exception:
            continue

    return None

def tokenize_expression(text: str) -> list[str]:
    """Split text into numeric and non-numeric tokens."""
    tokens = []
    current = []
    is_numeric = False

    for char in text:
        if not current:
            current.append(char)
            is_numeric = char.isnumeric()
            continue
        elif char.isnumeric() != is_numeric:
            tokens.append(''.join(current))
            current = [char]
            is_numeric = char.isnumeric()
        else:
            current.append(char)
    
    if current:
        tokens.append(''.join(current))
    
    return tokens

def normalize_numeric_text(text: str) -> str:
    """Normalize unicode numbers and fractions to standard ASCII digits."""
    text = unicodedata.normalize('NFKD', text)

    # Try direct float conversion first - most input will be normal!
    try:
        float(text)
        return text
    except ValueError:
        pass

    # Someone tried something weird. Let's try to parse it.
    tokens = tokenize_expression(text)
    
    result = []
    for token in tokens:
        if token.isnumeric():
            parsed = parse_number(token)
            if parsed is not None:
                result.append(str(parsed))
            else:
                raise ValueError("bad_numeric_input")
        else:
            result.append(token)
            
    return ''.join(result)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and verify if they follow the counting sequence."""
    message = update.message
    current_count = context.chat_data.get('count', 0)        

    try:
        text = normalize_numeric_text(message.text.strip())
        # Try to evaluate as mathematical expression first
        try:
            number = ne.evaluate(text)
        except (ValueError, SyntaxError, TypeError):
            number = None
            
        # If not an expression, try direct conversion
        if number is None:
            # Keep negative signs and decimal points
            cleaned = text.translate(str.maketrans('', '', PUNCTUATION_FILTER))
            number = float(cleaned)

        if number == current_count + 1:
            context.chat_data['count'] += 1
            if number == 69:
                await message.reply_text("nice")
            elif number == 420:
                await message.reply_text("/blaze")
        else:
            context.chat_data['count'] = 0
            await message.reply_text(f"Incorrect! The next number was {current_count + 1}. Count reset.")
            
    except ValueError as e:
        if e.args[0] == "bad_numeric_input":
            await message.reply_text("What kind of number is that? Try again.")
            return

async def handle_non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data['count'] = 0
    await update.message.reply_text("That's not even <i>text!</i>. Count reset.", parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the Counting Bot! Users must send sequential numbers starting from 1. "
        "Any wrong number will reset the count."
    )

async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current count for the chat."""
    current_count = context.chat_data.get('count', 0)
    await update.message.reply_text(f"Current count: {current_count}\nNext number should be: {current_count + 1}")

async def chat_migration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    application = context.application
    application.migrate_chat_data(message=message)

def main():
    """Start the bot."""
    dotenv.load_dotenv('.env')
    persistence = PicklePersistence(filepath='bot_data')
    application = Application.builder().token(os.environ.get('COUNTING_BOT_TOKEN')).persistence(persistence).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("count", get_count))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # application.add_handler(MessageHandler(~filters.TEXT & ~filters.StatusUpdate.ALL, handle_non_text_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, chat_migration))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()