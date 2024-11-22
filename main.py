import logging
from telegram import Update
from telegram import constants
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters, PicklePersistence
import dotenv
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and verify if they follow the counting sequence."""
    message = update.message
    try:
        current_count = context.chat_data.get('count', 0)
        number = int(message.text)

        if number == current_count + 1:
            context.chat_data['count'] = number
        else:
            context.chat_data['count'] = 0
            await message.delete()
            await message.reply_text(f"Incorrect! The next number was {current_count + 1}. Count reset.")
    except ValueError:
        context.chat_data['count'] = 0
        await message.delete()
        await message.reply_text(f"'{message.text}' ∉ **N**. Count reset.", parse_mode=constants.ParseMode.MARKDOWN_V2)

async def handle_non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data['count'] = 0
    await update.message.delete()
    await update.message.reply_text("That's not even *text!*. Count reset.", parse_mode=constants.ParseMode.MARKDOWN_V2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the Counting Bot! Users must send sequential numbers starting from 1. "
        "Any wrong number or non-number message will reset the count."
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
    application.add_handler(MessageHandler(~filters.TEXT, handle_non_text_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, chat_migration))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()