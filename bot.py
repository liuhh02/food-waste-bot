import logging
import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)
from googlemaps import Client as GoogleMaps
import os

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

LOCATION, PHOTO, DIET, SERVINGS, TIME, CONFIRMATION = range(6)

reply_keyboard = [['Confirm', 'Restart']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
TOKEN = 'YOURTELEGRAMBOTTOKEN'
bot = telegram.Bot(token=TOKEN)
chat_id = 'YOURTELEGRAMCHANNEL'
GMAPSAPI = 'YOURGOOGLEMAPSAPITOKEN'
gmaps = GoogleMaps(GMAPSAPI)

PORT = int(os.environ.get('PORT', 5000))

def facts_to_str(user_data):
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])


def start(update, context):
    update.message.reply_text(
        "Hi! I am your posting assistant to help you advertise your leftover food to reduce food waste. "
        "To start, please type the location of the leftover food.")
    return LOCATION


def location(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Location'
    text = update.message.text
    user_data[category] = text
    logger.info("Location of %s: %s", user.first_name, update.message.text)

    update.message.reply_text('I see! Please send a photo of the leftovers, '
                              'so users will know how the food looks like, or send /skip if you don\'t want to.')
    return PHOTO


def photo(update, context):
    user = update.message.from_user
    user_data = context.user_data
    photo_file = update.message.photo[-1].get_file()
    photo_file.download('user_photo.jpg')
    category = 'Photo Provided'
    user_data[category] = 'Yes'
    logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
    update.message.reply_text('Great! Is the food halal? Vegetarian? Please type in the dietary specifications of the food.')

    return DIET


def skip_photo(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Photo Provided'
    user_data[category] = 'No'
    logger.info("User %s did not send a photo.", user.first_name)
    update.message.reply_text('Is the food halal? Vegetarian? Please type in the dietary specifications of the food.')

    return DIET


def diet(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Dietary Specifications'
    text = update.message.text
    user_data[category] = text
    logger.info("Dietary Specification of food: %s", update.message.text)
    update.message.reply_text('How many servings are there?')

    return SERVINGS

def servings(update, context):
    user = update.message.from_user
    user_data = context.user_data
    category = 'Number of Servings'
    text = update.message.text
    user_data[category] = text
    logger.info("Number of servings: %s", update.message.text)
    update.message.reply_text('What time will the food be available until?')

    return TIME
    
def time(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Time to Take Food By'
	text = update.message.text
	user_data[category] = text
	logger.info("Time to Take Food By: %s", update.message.text)
	update.message.reply_text("Thank you for providing the information! Please check the information is correct:"
								"{}".format(facts_to_str(user_data)), reply_markup=markup)

	return CONFIRMATION

def confirmation(update, context):
    user_data = context.user_data
    user = update.message.from_user
    update.message.reply_text("Thank you! I will post the information on the channel @foodrescuers now.", reply_markup=ReplyKeyboardRemove())
    if (user_data['Photo Provided'] == 'Yes'):
        del user_data['Photo Provided']
        bot.send_photo(chat_id=chat_id, photo=open('user_photo.jpg', 'rb'), 
		caption="<b>Food is Available!</b> Check the details below: \n {}".format(facts_to_str(user_data)) +
		"\n For more information, message the poster {}".format(user.name), parse_mode=telegram.ParseMode.HTML)
    else:
        del user_data['Photo Provided']
        bot.sendMessage(chat_id=chat_id, 
            text="<b>Food is Available!</b> Check the details below: \n {}".format(facts_to_str(user_data)) +
        "\n For more information, message the poster {}".format(user.name), parse_mode=telegram.ParseMode.HTML)
    geocode_result = gmaps.geocode(user_data['Location'])
    lat = geocode_result[0]['geometry']['location'] ['lat']
    lng = geocode_result[0]['geometry']['location']['lng']
    bot.send_location(chat_id='@foodrescuers', latitude=lat, longitude=lng)

    return ConversationHandler.END

def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Bye! Hope to see you again next time.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={

            LOCATION: [CommandHandler('start', start), MessageHandler(Filters.text, gender)],

            PHOTO: [CommandHandler('start', start), MessageHandler(Filters.photo, photo),
                    CommandHandler('skip', skip_photo)],

            DIET: [CommandHandler('start', start), MessageHandler(Filters.text, location)],

            SERVINGS: [CommandHandler('start', start), MessageHandler(Filters.text, bio)],

            TIME: [CommandHandler('start', start), MessageHandler(Filters.text, time)],

            CONFIRMATION: [MessageHandler(Filters.regex('^Confirm$'),
                                      done),
            MessageHandler(Filters.regex('^Restart$'),
                                      start)
                       ]

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook('https://YOURHEROKUAPPNAME.herokuapp.com/' + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
