# Automated Blog Posting

This repo now includes an automatic scheduler powered by a webhook.

## Files

- `automation/monthly_posts.json`: scheduled post slots (currently 10 per month for 6 months).
- `scripts/auto_post.py`: checks due posts and sends them.
- `scripts/install_autopost_cron.sh`: installs cron entry to run automatically.
- `automation/.autopost_state.json`: created automatically to track posted items.
- `automation/autopost.log`: cron output log.

## 1) Set webhook URL

Set your webhook endpoint (Zapier/Make/Buffer/custom API):

```bash
export AUTOPOST_WEBHOOK_URL="https://your-webhook-url"
export AUTOPOST_TIMEZONE="Asia/Kolkata"
```

To persist it in your shell:

```bash
echo 'export AUTOPOST_WEBHOOK_URL="https://your-webhook-url"' >> ~/.zshrc
echo 'export AUTOPOST_TIMEZONE="Asia/Kolkata"' >> ~/.zshrc
source ~/.zshrc
```

## 2) Test once (safe)

```bash
python3 scripts/auto_post.py --dry-run

# Check the next planned slots quickly
python3 -m json.tool automation/monthly_posts.json | head -n 40
```

## 3) Enable automatic schedule

Runs every hour and publishes only posts whose `publish_at` time has passed:

```bash
bash scripts/install_autopost_cron.sh
```

## 4) Verify cron

```bash
crontab -l
tail -f automation/autopost.log
```

## Payload format sent to webhook

```json
{
  "id": "blog-2026-05-01-01",
  "ready": true,
  "title": "Your Blog Title",
  "body": "Post body text",
  "publish_at": "2026-04-26T09:00:00+05:30",
  "posted_at": "2026-04-26T09:01:05+05:30"
}
```

## Slot workflow

- Each slot includes `ready: false` by default.
- When you send a story, update that slot's `title`, `body`, and set `ready: true`.
- The scheduler publishes only due posts with `ready: true`.
