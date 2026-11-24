// Beta System: chapter announcement bot for Mr_Hobbyist's Workshop.
// Runs free on Cloudflare Workers. It only wakes up when someone uses /announce,
// so there's no server to keep running and nothing runs on your PC.
//
// Settings (Cloudflare → your worker → Settings → Variables and Secrets):
//   DISCORD_PUBLIC_KEY   Developer Portal → General Information → Public Key
//   DISCORD_APP_ID       Developer Portal → General Information → Application ID
//   DISCORD_TOKEN        Developer Portal → Bot → Reset Token        (type: Secret)
//   REGISTER_KEY         any password you make up, used once to set up /announce (type: Secret)
// Optional:
//   BOOK_URL             defaults to the Beta System WebNovel page
//   READER_ROLE_ID       defaults to the Beta System Reader role
//   UPDATES_CHANNEL      channel name to post in, defaults to "beta-updates"

const DEFAULT_BOOK_URL = "https://www.webnovel.com/book/37537402300791405";
const DEFAULT_ROLE_ID = "1574561456740106412";
const DEFAULT_CHANNEL = "beta-updates";
const EMBED_COLOR = 0x4fa3d9;
const API = "https://discord.com/api/v10";

// Permission bits
const ADMINISTRATOR = 1n << 3n;
const MANAGE_MESSAGES = 1n << 13n;

// ─────────────────────────────────────────────── the System's voice
// Edit these freely. One is picked at random for each announcement.

const HEADERS = [
  "[SYSTEM NOTICE v0.0.{build}]",
  "⚠ BETA BUILD ALERT ⚠",
  "[!] UNSCHEDULED PATCH DEPLOYED",
  ">> SYSTEM MESSAGE // BUILD {build} (UNSTABLE)",
  "[QUEST UPDATE]",
];

const LINES = [
  "New chapter detected. Please do not panic. Panicking is a premium feature.",
  "Patch notes: the Host suffered. You may now read about it.",
  "ERR_CHAPTER_OVERFLOW: content deployed anyway. QA was skipped. QA is always skipped.",
  "Quest available: **Read the new chapter**.\nReward: ██████. Penalty for ignoring: emotional damage (estimated).",
  "I was told to be professional. This is me being professional: NEW CHAPTER.",
  "Chapter uploaded successfully. Probably. 97.2% confidence.",
  "This notification was supposed to arrive with a fanfare sound. Audio module not found.",
  "A new chapter has spawned. It is not a gate. Probably. Approach anyway.",
  "Reminder: the finished Systems get cool notifications. You get me. Anyway, new chapter.",
  "Daily Quest progress: 0/1 chapters read. Fix that.",
];

const FOOTERS = [
  "Beta System v0.{minor}.{build} • unstable build",
  "Beta System • this build has not been reviewed",
  "Beta System • please report bugs to nobody",
];

const GLITCH_CHARS = "█▓▒░";

const pick = (list) => list[Math.floor(Math.random() * list.length)];
const build = () => String(100 + Math.floor(Math.random() * 900));
const fill = (text) =>
  text.replaceAll("{build}", build()).replaceAll("{minor}", String(1 + Math.floor(Math.random() * 9)));

function glitch(text, rate = 0.04) {
  if (text.includes("http") || text.includes("<")) return text;
  return [...text]
    .map((ch) => (/[a-z]/i.test(ch) && Math.random() < rate ? pick([...GLITCH_CHARS]) : ch))
    .join("");
}

export function buildAnnouncement({ title, line, bookUrl, roleId }) {
  const flavor = line && line.trim() ? line.trim() : pick(LINES);
  return {
    content: roleId ? `<@&${roleId}> N-N-New chapter alert.` : null,
    embeds: [
      {
        author: { name: fill(pick(HEADERS)) },
        title: title.slice(0, 256),
        url: bookUrl,
        description: `${glitch(flavor)}\n\n**[▶ Read Beta System on WebNovel](${bookUrl})**`,
        color: EMBED_COLOR,
        footer: { text: fill(pick(FOOTERS)) },
      },
    ],
    allowed_mentions: { parse: [], roles: roleId ? [roleId] : [] },
  };
}

// ─────────────────────────────────────────────── the /announce command

export const COMMAND = {
  name: "announce",
  description: "Announce a new Beta System chapter in #beta-updates.",
  type: 1,
  default_member_permissions: String(MANAGE_MESSAGES), // only mods/admins see it
  contexts: [0], // servers only, not DMs
  options: [
    { type: 3, name: "title", description: "Chapter title, e.g. Chapter 12: Gate Break", required: true, max_length: 256 },
    { type: 3, name: "line", description: "Optional: your own line from the System (blank = random)", required: false, max_length: 900 },
    { type: 5, name: "preview", description: "Only show it to you, don't post it", required: false },
  ],
};

// ─────────────────────────────────────────────── helpers

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  return bytes;
}

export async function verifyDiscordRequest(request, publicKey) {
  const signature = request.headers.get("x-signature-ed25519");
  const timestamp = request.headers.get("x-signature-timestamp");
  const body = await request.text();
  if (!signature || !timestamp || !publicKey) return { valid: false, body };
  try {
    const key = await crypto.subtle.importKey("raw", hexToBytes(publicKey), { name: "Ed25519" }, false, ["verify"]);
    const valid = await crypto.subtle.verify(
      "Ed25519",
      key,
      hexToBytes(signature),
      new TextEncoder().encode(timestamp + body),
    );
    return { valid, body };
  } catch {
    return { valid: false, body };
  }
}

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });

async function discord(env, method, path, body) {
  const res = await fetch(API + path, {
    method,
    headers: { Authorization: `Bot ${env.DISCORD_TOKEN}`, "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

function canAnnounce(member) {
  const perms = BigInt(member?.permissions ?? "0");
  return (perms & ADMINISTRATOR) !== 0n || (perms & MANAGE_MESSAGES) !== 0n;
}

async function findUpdatesChannel(env, guildId) {
  const wanted = (env.UPDATES_CHANNEL || DEFAULT_CHANNEL).toLowerCase();
  const channels = await discord(env, "GET", `/guilds/${guildId}/channels`);
  return channels.find((c) => (c.type === 0 || c.type === 5) && c.name.toLowerCase().includes(wanted));
}

async function postAnnouncement(env, interaction, options) {
  const followup = `/webhooks/${env.DISCORD_APP_ID}/${interaction.token}/messages/@original`;
  try {
    const channel = await findUpdatesChannel(env, interaction.guild_id);
    if (!channel) throw new Error(`Couldn't find a channel named "${env.UPDATES_CHANNEL || DEFAULT_CHANNEL}".`);
    const message = await discord(env, "POST", `/channels/${channel.id}/messages`, buildAnnouncement(options));
    if (channel.type === 5) {
      // Announcement channel: "Publish" it so servers following the channel get it too.
      await discord(env, "POST", `/channels/${channel.id}/messages/${message.id}/crosspost`).catch(() => {});
    }
    await discord(env, "PATCH", followup, {
      content: `✅ Announcement deployed in <#${channel.id}>. The System is… cautiously proud.`,
    });
  } catch (err) {
    await discord(env, "PATCH", followup, {
      content: `❌ ERR_DEPLOY_FAILED. Nothing was posted.\n\`${String(err.message).slice(0, 1500)}\``,
    }).catch(() => {});
  }
}

// ─────────────────────────────────────────────── request handling

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // One-time setup: visit https://<your-worker>/register?key=<REGISTER_KEY>
    if (request.method === "GET" && url.pathname === "/register") {
      if (!env.REGISTER_KEY || url.searchParams.get("key") !== env.REGISTER_KEY) {
        return new Response("Wrong or missing key.", { status: 403 });
      }
      try {
        await discord(env, "PUT", `/applications/${env.DISCORD_APP_ID}/commands`, [COMMAND]);
        return new Response("✅ /announce is registered. You can close this tab.");
      } catch (err) {
        return new Response(`❌ ${err.message}`, { status: 500 });
      }
    }

    if (request.method === "GET") {
      return new Response("Beta System online. Stability: 63% (rounded up out of pity).");
    }
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });

    const { valid, body } = await verifyDiscordRequest(request, env.DISCORD_PUBLIC_KEY);
    if (!valid) return new Response("Bad request signature.", { status: 401 });
    const interaction = JSON.parse(body);

    if (interaction.type === 1) return json({ type: 1 }); // Discord's PING check

    if (interaction.type === 2 && interaction.data?.name === "announce") {
      const ephemeral = 64;
      if (!interaction.guild_id) {
        return json({ type: 4, data: { content: "This only works in the server.", flags: ephemeral } });
      }
      if (!canAnnounce(interaction.member)) {
        return json({ type: 4, data: { content: "ERR_ACCESS_DENIED: Author and Moderators only.", flags: ephemeral } });
      }
      const opts = Object.fromEntries((interaction.data.options || []).map((o) => [o.name, o.value]));
      const options = {
        title: String(opts.title || "").trim(),
        line: opts.line,
        bookUrl: env.BOOK_URL || DEFAULT_BOOK_URL,
        roleId: env.READER_ROLE_ID || DEFAULT_ROLE_ID,
      };

      if (opts.preview) {
        const preview = buildAnnouncement(options);
        return json({
          type: 4,
          data: {
            content: "👁 Preview only (nothing posted, nobody pinged):",
            embeds: preview.embeds,
            flags: ephemeral,
            allowed_mentions: { parse: [] },
          },
        });
      }

      ctx.waitUntil(postAnnouncement(env, interaction, options));
      return json({ type: 5, data: { flags: ephemeral } }); // "Beta System is thinking…"
    }

    return json({ type: 4, data: { content: "Unknown command.", flags: 64 } });
  },
};
