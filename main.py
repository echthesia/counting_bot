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
import re

PUNCTUATION_FILTER = ''.join(c for c in string.punctuation if c not in '-.')

def parse_number(text: str) -> float | None:
    """Parse number string using multiple numeral systems."""
    # Locales with different numeral systems
    locales = ['zh-u-nu-traditio', 'ar', 'fa', 'bn', 'hi-u-nu-traditio', 'th-u-nu-traditio', 'ta-u-nu-traditio', 'am-u-nu-traditio', 'ti-u-nu-traditio', 'my', 'km-u-nu-traditio', 'lo-u-nu-traditio', 'gu-u-nu-traditio', 'pa-u-nu-traditio']
    
    # Try direct float conversion first
    try:
        return float(text)
    except ValueError:
        pass
    
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
        if char.isnumeric() != is_numeric:
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