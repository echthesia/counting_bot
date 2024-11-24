import ast
import logging
import string
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters, PicklePersistence
import dotenv
import os
from telegram.constants import ParseMode
import unicodedata

PUNCTUATION_FILTER = ''.join(c for c in string.punctuation if c not in '-.')

def safe_eval(expr):
    """Safely evaluate simple mathematical expressions."""
    try:
        # Convert common mathematical notation
        expr = expr.replace('×', '*').replace('÷', '/')
        # Parse and evaluate expression
        return float(ast.literal_eval(expr))
    except (ValueError, SyntaxError, TypeError):
        return None

def normalize_numeric_text(text: str) -> str:
    """Normalize unicode numbers and fractions to standard ASCII digits."""
    # Common unicode fractions and their decimal equivalents
    FRACTION_MAP = {
        '½': '0.5', '⅓': '0.333', '⅔': '0.666',
        '¼': '0.25', '¾': '0.75', '⅕': '0.2',
        '⅖': '0.4', '⅗': '0.6', '⅘': '0.8',
        '⅙': '0.166', '⅚': '0.833', '⅐': '0.142',
        '⅛': '0.125', '⅜': '0.375', '⅝': '0.625',
        '⅞': '0.875', '⅑': '0.111', '⅒': '0.1'
    }
    
    # Replace special number characters
    NUMBER_MAP = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        '𝟎': '0', '𝟏': '1', '𝟐': '2', '𝟑': '3', '𝟒': '4',
        '𝟓': '5', '𝟔': '6', '𝟕': '7', '𝟖': '8', '𝟗': '9'
    }

    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Replace fractions
    for fraction, decimal in FRACTION_MAP.items():
        text = text.replace(fraction, decimal)
    
    # Replace special number characters
    for special, normal in NUMBER_MAP.items():
        text = text.replace(special, normal)
    
    return text

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
        number = safe_eval(text)
        
        # If not an expression, try direct conversion
        if number is None:
            # Keep negative signs and decimal points
            cleaned = text.translate(str.maketrans('', '', PUNCTUATION_FILTER))
            number = float(cleaned)

        if number == current_count + 1:
            context.chat_data['count'] = number
            if number == 69:
                await message.reply_text("nice")
            elif number == 420:
                await message.reply_text("/blaze")
        else:
            context.chat_data['count'] = 0
            await message.reply_text(f"Incorrect! The next number was {current_count + 1}. Count reset.")
            
    except (ValueError, SyntaxError, TypeError):
        pass

async def handle_non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data['count'] = 0
    await update.message.reply_text("That's not even <i>text!</i>. Count reset.", parse_mode=constants.ParseMode.HTML)

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