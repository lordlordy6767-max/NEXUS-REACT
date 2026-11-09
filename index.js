const http = require('http');
http.createServer((req, res) => res.end('NEXUS REACT is online')).listen(process.env.PORT || 3000);
const { Client, GatewayIntentBits, Partials, EmbedBuilder } = require('discord.js');
const fs = require('fs');
const config = require('./config.js');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMessageReactions],
  partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

// --- DATABASE (simple JSON) ---
let db = { premium: {}, autoreactChannel: {}, autoreactUser: {}, tagreact: {}, presets: {} };
if (fs.existsSync('./db.json')) db = JSON.parse(fs.readFileSync('./db.json'));
function save() { fs.writeFileSync('./db.json', JSON.stringify(db, null, 2)); }

// --- HELPERS ---
const isOwner = (id) => id === config.OWNER_ID;
const hasPremium = (id) => isOwner(id) || (db.premium[id] && db.premium[id] > Date.now());
const premiumMsg = () => `❌ PREMIUM only! DM ${config.OWNER_USERNAME} to buy 👑`;
const ownerOnlyMsg = () => `❌ Only the Owner can do this. DM ${config.OWNER_USERNAME} for coins / premium.`;

function parseTime(str) {
  const map = { s: 1000, m: 60000, h: 3600000, d: 86400000, mo: 2592000000, y: 31536000000 };
  const m = str.match(/^(\d+)(s|mo|m|h|d|y)$/);
  if (!m) return null;
  return parseInt(m[1]) * map[m[2]];
}

client.on('ready', () => console.log(`✅ NEXUS REACT logged in as ${client.user.tag}`));

// --- TAG REACT + AUTOREACT ---
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  // TAG REACT - if someone tags owner
  if (message.mentions.users.has(config.OWNER_ID)) {
    const emojis = db.tagreact[config.OWNER_ID];
    if (emojis) {
      for (const e of emojis) {
        try { await message.react(e); } catch {}
      }
    }
  }

  // AUTOREACT CHANNEL
  const chanEmojis = db.autoreactChannel[message.channel.id];
  if (chanEmojis) {
    for (const e of chanEmojis) { try { await message.react(e); } catch {} }
  }

  // AUTOREACT USER
  const userEmojis = db.autoreactUser[message.author.id];
  if (userEmojis) {
    for (const e of userEmojis) { try { await message.react(e); } catch {} }
  }

  if (!message.content.startsWith(config.PREFIX)) return;
  const args = message.content.slice(1).trim().split(/ +/);
  const cmd = args.shift().toLowerCase();

  // --- PREMIUM COMMANDS (Owner Only) ---
  if (cmd === 'premium') {
    if (!isOwner(message.author.id)) return message.reply(ownerOnlyMsg());
    const target = message.mentions.users.first();
    const time = args[1];
    if (!target || !time) return message.reply('Usage: `!premium @user 30s / 10m / 2h / 7d / 1mo / 1y`');
    const ms = parseTime(time);
    if (!ms) return message.reply('Bad time. Use 30s / 10m / 2h / 7d / 1mo / 1y');
    db.premium[target.id] = Date.now() + ms;
    save();
    return message.reply(`✅ ${target} got PREMIUM for ${time} 👑`);
  }
  if (cmd === 'remove-premium') {
    if (!isOwner(message.author.id)) return message.reply(ownerOnlyMsg());
    const target = message.mentions.users.first();
    delete db.premium[target.id]; save();
    return message.reply(`✅ Removed PREMIUM from ${target}`);
  }
  if (cmd === 'premium-check') {
    const target = message.mentions.users.first() || message.author;
    return message.reply(hasPremium(target.id) ? `✅ ${target} has PREMIUM 👑` : `❌ ${target} has NO premium`);
  }

  // --- REACT ---
  if (cmd === 'react') {
    const link = args[0];
    const emojis = args.slice(1);
    if (!link || emojis.length === 0) return message.reply('Usage: `!react <message link> 🔥 ❤️`');
    if (!hasPremium(message.author.id) && emojis.length > 3) return message.reply(premiumMsg());
    if (hasPremium(message.author.id) && emojis.length > 20) return message.reply('Max 20 emojis');
    const match = link.match(/channels\/\d+\/(\d+)\/(\d+)/);
    if (!match) return message.reply('Bad message link');
    try {
      const channel = await client.channels.fetch(match[1]);
      const targetMsg = await channel.messages.fetch(match[2]);
      for (const e of emojis) { try { await targetMsg.react(e); } catch {} }
      return message.reply(`✅ Reacted with ${emojis.length} emojis`);
    } catch { return message.reply('❌ Could not find that message. Bot must be in that server.'); }
  }

  // --- AUTOREACT ---
  if (cmd === 'autoreact') {
    const sub = args[0];
    if (sub === 'list') {
      return message.reply(`**Your Autoreact:**\nChannels: ${JSON.stringify(db.autoreactChannel)}\nUsers: ${JSON.stringify(db.autoreactUser)}`);
    }
    if (sub === 'add') {
      if (!hasPremium(message.author.id)) return message.reply(premiumMsg());
      const target = message.mentions.channels.first() || message.mentions.users.first();
      const emojis = args.slice(1).filter(a => !a.startsWith('<#') && !a.startsWith('<@'));
      if (!target) return message.reply('Usage: `!autoreact add #channel 🔥` or `!autoreact add @user 🔥`');
      if (target.type === 0) db.autoreactChannel[target.id] = emojis;
      else db.autoreactUser[target.id] = emojis;
      save();
      return message.reply(`✅ Autoreact added for ${target} : ${emojis.join(' ')}`);
    }
    if (sub === 'remove') {
      const target = message.mentions.channels.first() || message.mentions.users.first();
      delete db.autoreactChannel[target.id]; delete db.autoreactUser[target.id]; save();
      return message.reply(`✅ Autoreact removed for ${target}`);
    }
    if (sub === 'on' || sub === 'off') {
      // simple toggle - store globally for owner
      db.autoreactEnabled = sub === 'on'; save();
      return message.reply(`✅ Autoreact ${sub}`);
    }
  }

  // --- REACT-ALL / REACT-BOOST ---
  if (cmd === 'react-all') {
    if (!hasPremium(message.author.id)) return message.reply(premiumMsg());
    const emojis = args;
    const msgs = await message.channel.messages.fetch({ limit: 10 });
    for (const [, m] of msgs) for (const e of emojis) { try { await m.react(e); } catch {} }
    return message.reply('✅ Reacted to last 10 messages');
  }
  if (cmd === 'react-boost') {
    if (!hasPremium(message.author.id)) return message.reply(premiumMsg());
    const emojis = db.tagreact[message.author.id] || ['🔥','👑','💎'];
    const msgs = await message.channel.messages.fetch({ limit: 5 });
    const last = msgs.find(m => m.author.id === message.author.id);
    if (last) for (const e of emojis) { try { await last.react(e); } catch {} }
    return message.reply('✅ Boosted your last message');
  }

  // --- TAG REACT ---
  if (cmd === 'tagreact') {
    const sub = args[0];
    if (sub === 'on') {
      if (!hasPremium(message.author.id)) return message.reply(premiumMsg());
      const emojis = args.slice(1);
      db.tagreact[message.author.id] = emojis; save();
      return message.reply(`✅ TAG REACT ON: ${emojis.join(' ')} - When anyone tags you, bot will react 👑`);
    }
    if (sub === 'set') {
      const emojis = args.slice(1);
      db.tagreact[message.author.id] = emojis; save();
      return message.reply(`✅ Tag react updated: ${emojis.join(' ')}`);
    }
    if (sub === 'off') { delete db.tagreact[message.author.id]; save(); return message.reply('✅ Tag react OFF'); }
    if (sub === 'list') {
      const e = db.tagreact[message.author.id];
      return message.reply(e ? `Your tag react: ${e.join(' ')}` : 'No tag react set. Use `!tagreact on 👑 🔥 💎`');
    }
  }

  // --- CLAIM OWNER (Recovery) ---
  if (cmd === 'claim-owner') {
    if (args[0] === config.RECOVERY_KEY) {
      config.OWNER_ID = message.author.id;
      return message.reply('✅ You are now the Owner! Change OWNER_ID in config too.');
    } else return message.reply('❌ Wrong key');
  }
});

console.log('TOKEN CHECK - length:', process.env.DISCORD_TOKEN ? process.env.DISCORD_TOKEN.length : 'MISSING');
client.login(process.env.DISCORD_TOKEN.trim()).then(() => console.log('LOGIN SUCCESS - BOT IS ONLINE')).catch(err => console.log('LOGIN FAILED:', err.message));
client.on('clientReady', () => console.log('NEXUS REACT logged in as', client.user.tag));
client.on('ready', () => console.log('NEXUS REACT logged in as', client.user.tag));
