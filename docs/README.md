# 🤖 Teo - Personal Assistant Bot

Teo is your personal Telegram assistant that helps simplify your life. Currently features weather notifications with plans for expansion.

## ✨ Features

- 🌤 **Current Weather**: Get instant weather updates for any city
- 📅 **Weather Forecasts**: 3-day weather forecasts
- 🔔 **Daily Notifications**: Automated daily weather notifications
- ⚙️ **Customizable Settings**: Set your city, timezone, and notification preferences
- 🌍 **Multi-timezone Support**: Works with any timezone
- 📱 **Interactive Interface**: Easy-to-use buttons and commands

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- A Telegram account
- OpenWeatherMap API account (free)

### 2. Setup

1. **Clone or download this project**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a Telegram Bot:**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Use `/newbot` command and follow instructions
   - Save the bot token you receive

4. **Get Weather API Key:**
   - Sign up at [OpenWeatherMap](https://openweathermap.org/api)
   - Get your free API key

5. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your credentials:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   WEATHER_API_KEY=your_weather_api_key_here
   DEFAULT_CITY=Your City
   TIMEZONE=Your/Timezone
   ```

6. **Run the Bot:**
   ```bash
   python main.py
   ```

### 3. Start Using Teo

1. Find your bot on Telegram (use the username you set with BotFather)
2. Send `/start` to begin
3. Set your city with `/setcity Your City`
4. Enable notifications with `/notifications`

## 📋 Commands

### Basic Commands
- `/start` - Initialize the bot and see welcome message
- `/help` - Show all available commands
- `/weather [city]` - Get current weather (uses your default city if not specified)
- `/forecast [city]` - Get 3-day weather forecast

### Settings Commands
- `/setcity <city>` - Set your default city
- `/notifications` - Manage daily weather notifications
- `/settings` - View your current settings
- `/timezone <timezone>` - Set your timezone

### Examples
```
/weather London
/setcity New York
/timezone America/New_York
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token (required) | - |
| `WEATHER_API_KEY` | OpenWeatherMap API key (required) | - |
| `DEFAULT_CITY` | Default city for new users | London |
| `TIMEZONE` | Default timezone | UTC |

### Supported Timezones

Use standard timezone names like:
- `UTC`
- `Europe/London`
- `America/New_York`
- `Asia/Tokyo`
- `Australia/Sydney`

## 📱 Usage Examples

### Setting up notifications:
1. `/setcity London` - Set your city
2. `/notifications` - Open notification settings
3. Click "🟢 Enable" to turn on daily notifications
4. Use "⏰ Change Time" to set when you want to receive them

### Getting weather information:
- `/weather` - Current weather for your default city
- `/weather Tokyo` - Current weather for Tokyo
- `/forecast` - 3-day forecast for your default city
- `/forecast Paris` - 3-day forecast for Paris

## 🛠 Development

### Project Structure
```
TEO/
├── main.py                 # Entry point
├── teo_bot.py             # Main bot logic
├── weather_service.py     # Weather API integration
├── notification_scheduler.py # Notification scheduling
├── config.py              # Configuration management
├── requirements.txt       # Dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

### Adding New Features

The bot is designed to be easily extensible. To add new features:

1. Add new command handlers in `teo_bot.py`
2. Create service modules for external APIs
3. Update the help text and README

## 🐛 Troubleshooting

### Common Issues

**Bot doesn't respond:**
- Check if your bot token is correct in `.env`
- Ensure the bot is running (`python main.py`)
- Verify you've started a chat with the bot (`/start`)

**Weather not working:**
- Verify your OpenWeatherMap API key is valid
- Check if the city name is spelled correctly
- Try using a different city name format

**Notifications not working:**
- Ensure notifications are enabled (`/notifications`)
- Check your timezone setting (`/settings`)
- Verify the notification time is set correctly

### Logs

The bot logs important information to the console. Check the logs if something isn't working as expected.

## 🔮 Future Features

- 📊 Weather trends and analytics
- 🎯 Location-based smart suggestions
- 📅 Calendar integration
- 🏠 Smart home control
- 💼 Task management
- 📰 News briefings
- 🚗 Traffic updates

## 📄 License

This project is open source. Feel free to modify and extend it for your needs!

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

---

**Enjoy using Teo! 🤖✨**


