# Beta System bot: `/announce`

A custom Discord bot with its own name and avatar. Only you and Moderators can use it.

Type **`/announce title: Chapter 12: Gate Break`** in any channel and the bot posts this in **#beta-updates**:
- a ping for **@Beta System Reader**
- a glitchy System header and a random sarcastic line (or your own line, using the optional `line:` box)
- the chapter title
- your **Beta System WebNovel page**, which is the only link in the post

Add `preview: True` to see the post privately first. Nothing gets posted and nobody gets pinged.

The bot runs free on **Cloudflare Workers**. It only wakes up when you use the command, so nothing runs on your PC and there's no server to look after.

---

## One-time setup (about 15 minutes)

### 1. Create the bot in Discord
1. Go to <https://discord.com/developers/applications>, click **New Application**, name it **Beta System** and click Create.
2. On **General Information**, upload the avatar, add a description if you like, and keep this page open. You'll need the **Application ID** and **Public Key** from it.
3. On the **Bot** tab:
   - Upload the same avatar (and a banner if you have one).
   - Click **Reset Token** and copy the token. **This is the bot's password. Never share it or post it anywhere.**
   - Turn **Public Bot** off so only you can add it to servers.

### 2. Put the bot online (Cloudflare, free)
1. Sign up at <https://dash.cloudflare.com/sign-up>. It's free, and no card is needed for Workers.
2. Go to **Workers & Pages → Create → Create Worker** (the "Hello World" starter), name it `beta-system` and click **Deploy**.
3. Click **Edit code**, delete everything there, paste in all of `worker.js` from this folder, then click **Deploy**.
4. Go back to the worker and open **Settings → Variables and Secrets → Add**. Add these four:

| Name | Type | Value |
|---|---|---|
| `DISCORD_PUBLIC_KEY` | Text | Public Key from step 1 |
| `DISCORD_APP_ID` | Text | Application ID from step 1 |
| `DISCORD_TOKEN` | **Secret** | bot token from step 1 |
| `REGISTER_KEY` | **Secret** | any made-up password, e.g. `glitchy-prototype-42` |

5. Copy your worker's address from the top of its page. It looks like `https://beta-system.YOUR-NAME.workers.dev`.

### 3. Connect Discord to it
1. **Register the command:** open `https://beta-system.YOUR-NAME.workers.dev/register?key=YOUR-REGISTER-KEY` in your browser. It should say "/announce is registered".
2. **Developer Portal → General Information → Interactions Endpoint URL:** paste the worker address (`https://beta-system.YOUR-NAME.workers.dev`) and click **Save Changes**. Discord tests it right away. A green "All your edits have been carefully recorded" message means it works.

### 4. Invite the bot to the server
Open this link after replacing `YOUR_APP_ID`, pick **Mr_Hobbyist's Workshop** and click Authorize:

```
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=216064
```

Then let it post in #beta-updates, since members can't post there by default. Go to **#beta-updates → Edit Channel → Permissions → Advanced permissions → + → Beta System**, allow **Send Messages** and click Save.

Done! Try `/announce title: Test preview: True`.

---

## Changing things
- **The System's lines:** edit the lists at the top of `worker.js` in Cloudflare (**Edit code**), then click **Deploy**.
- **Different book or channel:** add `BOOK_URL`, `UPDATES_CHANNEL` (part of the channel name, e.g. `keepers-updates`) or `READER_ROLE_ID` as variables.
- **Who can use it:** anyone with the **Manage Messages** permission or Administrator, which means your Author and Moderator roles.
