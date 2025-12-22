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
