# Beta System chapter notifier (free, runs on GitHub)

GitHub runs this for free every 15 minutes, so you don't need a server and your PC can be off. Each run checks WebNovel once. If there's a new chapter, it posts in **#beta-updates** as "Beta System", pings **@Beta System Reader**, and speaks in the System's sarcastic, glitchy voice.

What's different from the full bot: there are no slash commands (`/latest`, `/status` and so on), and announcements can land a few minutes after the chapter goes up. Everything else works the same: the first run records existing chapters without announcing them, big batches go out as one post, and problems are reported in #mod-logs.

---

## 1. Make two webhooks in Discord (2 minutes)
A webhook is a private posting address for one channel.

1. Go to #beta-updates, click Edit Channel, then **Integrations → Webhooks → New Webhook**. Name it `Beta System` and click **Copy Webhook URL**.
2. Optional, for error reports: do the same in #mod-logs.

**Treat webhook URLs like passwords.** Anyone who has one can post in that channel.

## 2. Get the role ID
Turn on Developer Mode under User Settings → Advanced. Then go to Server Settings → Roles, click `...` next to **Beta System Reader**, and choose **Copy Role ID**.

## 3. Put the code on GitHub
1. Sign up for a free account at <https://github.com>.
2. Click **+ → New repository**. Name it `beta-system-bot`, set it to **Public** and click Create.
   - It has to be public because GitHub's timers only run free without limits on public repos. Only the code is visible. Your webhook links stay hidden in Secrets (step 4).
3. Click **uploading an existing file**, drag in every file from this folder **including the `.github` folder**, and click **Commit changes**.
   - If the `.github` folder doesn't upload: click **Add file → Create new file**, type `.github/workflows/check-chapters.yml` as the name, paste in that file's contents and commit.

## 4. Add your settings as Secrets
In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Name | Value |
|---|---|
| `DISCORD_WEBHOOK_URL` | the #beta-updates webhook URL |
| `WEBNOVEL_BOOK` | `https://www.webnovel.com/book/37537402300791405` |
| `READER_ROLE_ID` | the Beta System Reader role ID |
| `MOD_WEBHOOK_URL` | the #mod-logs webhook URL (optional) |
| `BOT_AVATAR_URL` | a link to an avatar image (optional) |

## 5. Turn it on
1. Open the **Actions** tab. If GitHub asks, click to enable workflows.
2. Click **Check for new chapters → Run workflow** to do the first run now. It should finish with a green check. If you added the mod webhook, #mod-logs gets a "Calibration complete" message.
3. From then on it runs by itself every 15 minutes.

## Good to know
- **It keeps itself running.** GitHub pauses timers on repos with no activity for 60 days. The bot updates `state.json` at least every 45 days so that doesn't happen.
- **If something breaks,** the Actions tab shows a red X and the log for each run. After 3 failed checks in a row, the System also complains in #mod-logs.
- **To change what the System says,** edit `voice.py` right on GitHub (click the file, then the pencil icon).
- **Posts aren't auto-published.** #beta-updates is an Announcement channel, and webhooks can't click "Publish". That only matters if other servers follow the channel, and none do yet.
- **To pause it,** go to the Actions tab, click the workflow, then the `...` menu, then **Disable workflow**.
