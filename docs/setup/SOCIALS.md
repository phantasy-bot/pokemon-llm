# Twitter/X API Setup

This guide covers setting up the X (Twitter) API for automated tweet posting during stream intros.

## Overview

The tweet generator posts AI-generated images with contextual tweets about Lass's Pokemon adventure. Tweets are first sent to Discord for community approval before posting to X.

## X API Tier Requirements

**Free Tier** (sufficient for this use case):
- 500 tweets per month
- Read and write access
- OAuth 1.0a User Context

## Setup Steps

### 1. Create a Developer Account

1. Go to [developer.twitter.com](https://developer.twitter.com/)
2. Sign in with your X account
3. Apply for a developer account (Free tier is fine)
4. Complete the application describing your bot use case

### 2. Create a Project and App

1. Navigate to the Developer Portal dashboard
2. Create a new Project (e.g., "Pokemon LLM Stream")
3. Create an App within the project (e.g., "Lass Bot")
4. Note your App ID for reference

### 3. Configure App Permissions

1. In your App settings, go to "User authentication settings"
2. Click "Set up" or "Edit"
3. Configure the following:
   - **App permissions**: Read and write
   - **Type of App**: Web App, Automated App, or Bot
   - **Callback URL**: `https://localhost/callback` (not used but required)
   - **Website URL**: Your stream URL or project page

### 4. Generate API Keys

1. Go to your App's "Keys and tokens" page
2. Generate/regenerate the following:

| Key Type | Description |
|----------|-------------|
| API Key | Your app's consumer key |
| API Key Secret | Your app's consumer secret |
| Access Token | User-level access token |
| Access Token Secret | User-level access token secret |

**Important**: The Access Token and Secret must be generated with Read+Write permissions. If you changed permissions, regenerate these tokens.

### 5. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Twitter/X API Configuration
TWITTER_ENABLED=true
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

## Testing the Connection

Run the following to test your credentials:

```python
import tweepy

auth = tweepy.OAuth1UserHandler(
    consumer_key="YOUR_API_KEY",
    consumer_secret="YOUR_API_SECRET",
    access_token="YOUR_ACCESS_TOKEN",
    access_token_secret="YOUR_ACCESS_TOKEN_SECRET"
)

api = tweepy.API(auth)
print(api.verify_credentials().screen_name)
```

## Rate Limits

### Free Tier Limits

| Endpoint | Limit |
|----------|-------|
| POST /2/tweets | 500/month |
| POST /1.1/media/upload | 500/month |
| API calls | 1,500/15 minutes |

### Best Practices

1. **One tweet per stream start**: Only post during intro sequence
2. **Skip on denial**: If Discord denies, don't retry
3. **Track monthly usage**: Log successful posts to stay under 500/month

## Troubleshooting

### 403 Forbidden Error

- Ensure app has Read+Write permissions
- Regenerate Access Token after permission changes
- Verify tokens are copied correctly (no extra whitespace)

### 401 Unauthorized Error

- Check API key/secret are correct
- Verify Access Token matches your account
- Ensure tokens haven't been revoked

### Media Upload Fails

- Image must be under 5MB
- Supported formats: PNG, JPEG, GIF, WEBP
- Use `image/png` or `image/jpeg` content type

### Rate Limit Exceeded

- Check if you've hit 500 tweets/month
- Wait 15 minutes if hitting per-window limit
- Consider upgrading to Basic tier ($100/month) for higher limits

## Security Notes

1. **Never commit `.env`** - It's in `.gitignore`
2. **Rotate tokens regularly** - Regenerate monthly
3. **Monitor activity** - Check X Developer dashboard for unusual activity
4. **Use environment variables** - Never hardcode credentials

## Related Documentation

- [Discord Setup](./DISCORD_SETUP.md) - Required for approval workflow
- [Tweet Generator](../services/tweet_generator.py) - Service implementation
- [Twitter Service](../services/twitter_service.py) - API client
# Discord Approval Bot Setup

This guide covers setting up the Discord bot for tweet approval workflow. The bot posts generated tweets to a designated channel where moderators can approve or deny them before posting to X.

## Overview

When a stream starts, the tweet generator:
1. Generates an AI image via ComfyUI
2. Generates tweet text via LLM
3. Posts to Discord with approval reactions
4. Waits for community vote
5. Posts to X if approved

## Discord Bot Setup

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it (e.g., "Lass Tweet Bot")
4. Accept the Terms of Service
5. Note your **Application ID** for later

### 2. Create the Bot

1. In your application, go to the "Bot" section
2. Click "Add Bot" and confirm
3. Configure bot settings:
   - **Public Bot**: Off (only you can add it)
   - **Requires OAuth2 Code Grant**: Off
   - **Message Content Intent**: On (required for reading messages)

### 3. Get the Bot Token

1. In the Bot section, click "Reset Token"
2. Copy the token immediately (shown only once)
3. Save it securely - you'll need it for `.env`

**Security Warning**: Never share or commit your bot token. Anyone with the token can control your bot.

### 4. Configure Bot Permissions

The bot needs these permissions:
- Send Messages
- Embed Links
- Attach Files
- Add Reactions
- Read Message History

**Permission Integer**: `117824`

### 5. Invite the Bot to Your Server

Generate an invite URL:

1. Go to "OAuth2" > "URL Generator"
2. Select scopes:
   - `bot`
   - `applications.commands` (optional, for slash commands)
3. Select permissions listed above (or use `117824`)
4. Copy the generated URL
5. Open in browser and select your server

Alternatively, construct the URL manually:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_APP_ID&permissions=117824&scope=bot
```

### 6. Get the Approval Channel ID

1. Enable Developer Mode in Discord:
   - User Settings > App Settings > Advanced > Developer Mode
2. Right-click your approval channel
3. Click "Copy Channel ID"

### 7. Configure Environment Variables

Add to your `.env` file:

```bash
# Discord Bot Configuration
DISCORD_ENABLED=true
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_APPROVAL_CHANNEL_ID=1234567890123456789
DISCORD_APPROVAL_TIMEOUT=900
DISCORD_APPROVAL_THRESHOLD=1
DISCORD_MAX_REGENERATIONS=3
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_ENABLED` | Enable/disable Discord approval | `false` |
| `DISCORD_BOT_TOKEN` | Bot token from Developer Portal | Required |
| `DISCORD_APPROVAL_CHANNEL_ID` | Channel ID for posting approvals | Required |
| `DISCORD_APPROVAL_TIMEOUT` | Seconds to wait for votes | `900` (15 min) |
| `DISCORD_APPROVAL_THRESHOLD` | Approve votes needed | `1` |
| `DISCORD_MAX_REGENERATIONS` | Max regeneration attempts | `3` |

## Approval Emoji Reference

The bot adds these reactions for voting:

| Emoji | Action | Description |
|-------|--------|-------------|
| :white_check_mark: | Approve | Post the tweet to X |
| :x: | Deny | Skip this tweet |
| :arrows_counterclockwise: | Regenerate All | New image + new text |
| :frame_with_picture: | Regenerate Image | Keep text, new image |
| :memo: | Regenerate Text | Keep image, new text |

## Approval Flow

```
Stream Start
    │
    ▼
Generate Image (ComfyUI)
    │
    ▼
Generate Tweet Text (LLM)
    │
    ▼
Post to Discord ──────────────────┐
    │                              │
    ▼                              │
Wait for Reactions                 │
    │                              │
    ├─── Approve ─── Post to X     │
    │                              │
    ├─── Deny ────── Skip          │
    │                              │
    ├─── Regen All ─ Loop Back ────┤
    │                              │
    ├─── Regen Img ─ Loop Back ────┤
    │                              │
    ├─── Regen Txt ─ Loop Back ────┤
    │                              │
    └─── Timeout ─── Skip          │
                                   │
    Max 3 regenerations ───────────┘
```

## Testing the Bot

### 1. Test Bot Connection

```python
import discord
import asyncio

async def test_bot():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        channel = client.get_channel(YOUR_CHANNEL_ID)
        if channel:
            await channel.send("Bot test message!")
        await client.close()
    
    await client.start("YOUR_BOT_TOKEN")

asyncio.run(test_bot())
```

### 2. Test Full Workflow

Set environment variables and run:

```bash
python -c "
from services.discord_service import create_discord_service
import asyncio

async def test():
    service = create_discord_service()
    if service.enabled:
        await service.start()
        result = await service.request_approval(
            tweet_text='Test tweet!',
            image_path=None,
            run_context={'test': True}
        )
        print(f'Result: {result}')
        await service.stop()
    else:
        print('Discord service not enabled')

asyncio.run(test())
"
```

## Troubleshooting

### Bot Doesn't Respond

1. Check bot token is correct
2. Verify bot has channel permissions
3. Ensure Message Content Intent is enabled
4. Check bot is online in Discord

### "Missing Permissions" Error

1. Re-invite bot with correct permissions
2. Check channel-specific permission overrides
3. Ensure bot role is above @everyone in role hierarchy

### Reactions Not Working

1. Verify "Add Reactions" permission
2. Check bot can read the channel
3. Ensure the message was sent by the bot

### Timeout Always Triggers

1. Check `DISCORD_APPROVAL_TIMEOUT` value
2. Verify you're reacting within the timeout window
3. Ensure reactions are on the correct message

## Security Notes

1. **Keep token secret**: Never commit `DISCORD_BOT_TOKEN`
2. **Limit channel access**: Only mods should access the approval channel
3. **Audit regularly**: Check bot activity in Server Settings > Audit Log
4. **Regenerate if leaked**: If token is exposed, regenerate immediately

## Related Documentation

- [Twitter Setup](./TWITTER_SETUP.md) - X API configuration
- [Tweet Generator](../services/tweet_generator.py) - Orchestration service
- [Discord Service](../services/discord_service.py) - Bot implementation
