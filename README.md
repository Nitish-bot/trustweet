# trustweet

An X (Twitter) bot that analyzes account trustworthiness when triggered with "riddle me this" in replies.

## Features

- **Comprehensive Analysis**: Evaluates account age, follower ratios, bio content, and trust network
- **Trust Network Integration**: Checks against curated trusted accounts list
- **Real-time Monitoring**: Continuously monitors for trigger phrases
- **Replit Ready**: Easy deployment on Replit with minimal setup

## Setup Instructions

### 1. Get X/Twitter API Access

1. Go to [X Developer Portal](https://developer.x.com/en/portal/petition/essential/basic-info)
2. Apply for free Essential access (sufficient for this bot)
3. Create a new app and generate:
   - Bearer Token
   - API Key & Secret
   - Access Token & Secret
   
Note: While using in production, you might want to increase the API calls which are very conservative for using a free account.

### 2. Configure Environment Variables

1. Copy `.env.example` to `.env`
2. Fill in your X API credentials:

```bash
X_BEARER_TOKEN=your_bearer_token_here
X_API_KEY=your_api_key_here
X_API_KEY_SECRET=your_api_key_secret_here
X_ACCESS_TOKEN=your_access_token_here
X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
RUN_ONCE=True
```

### 3. Install Dependencies

This project uses uv to manage deps which is highly supported on replit as well.

```bash
uv pip sync
```

### 4. Run the Bot

Change `RUN_ONCE` env variable to `false` for continuous monitoring or keep it to `true` for a single run. 

```bash
uv run main.py
```

## Replit Deployment

1. Import this repository to Replit
2. Set environment variables in Replit's Secrets tab:
   - `X_BEARER_TOKEN`
   - `X_API_KEY`
   - `X_API_KEY_SECRET`
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
   - `RUN_ONCE`
3. Click "Run" button

## How It Works

### Bot Workflow

1. **Monitor**: Searches for tweets containing "riddle me this"
2. **Identify**: Finds the original tweet being replied to
3. **Analyze**: Evaluates the original tweet author's trustworthiness
4. **Report**: Posts a concise analysis as a reply

### Analysis Factors

- **Account Age**: Older accounts score higher
- **Follower Ratio**: Balanced ratios indicate authenticity
- **Trust Network**: Connections to verified trusted accounts
- **Verification Status**: Official verification adds credibility
- **Bio Analysis**: Checks for suspicious patterns
- **Engagement Patterns**: Legitimate interaction history

### Trust Scoring

- 🟢 **LIKELY TRUSTWORTHY** (5+ points): Low risk, established presence
- 🟡 **PROCEED WITH CAUTION** (3-4 points): Some risk factors present
- 🔴 **HIGH RISK** (0-2 points): Multiple concerning factors

## Architecture

### Core Modules

- **`RugGuardBot`**: Main bot class handling all operations
- **`search_and_analyze_single_trigger()`**: Optimized single API call for detection and analysis
- **`analyze_account_from_data()`**: Processes user data without additional API calls
- **`generate_trustworthiness_report()`**: Creates concise analysis reports
- **`load_trusted_accounts()`**: Fetches trusted accounts from GitHub

### API Optimization

The bot is designed to minimize API calls:
- **Single Search Call**: Gets trigger tweets with all necessary user data
- **Batch Processing**: Analyzes multiple triggers in one API response
- **Data Reuse**: Uses included user data instead of separate lookups
- **Rate Limit Handling**: Built-in delays and retry logic

### File Structure

```
rugguard-bot/
├── main.py              # Main bot script
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── README.md           # This file
└── .gitignore          # Git ignore rules
```

## Configuration

- **Check Interval**: Modify `check_interval` in `run_continuous()`
- **Trust Scoring**: Adjust scoring logic in `generate_trustworthiness_report()`
- **Trigger Phrase**: Change `self.trigger_phrase` for different activation
