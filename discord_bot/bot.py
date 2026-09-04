"""Discord bot for Runbook - listens for incident reports and triggers the AI pipeline."""
import os
import sys
import discord
import aiohttp
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Runbook bot connected as {client.user}")
    print(f"Backend URL: {BACKEND_URL}")
    print("Listening for incident reports...")


@client.event
async def on_message(message):
    print(f"[DEBUG] Received message from {message.author}: '{message.content}'")

    # Ignore own messages
    if message.author == client.user:
        return

    # Trigger on messages that start with !incident or in a designated channel
    content = message.content.strip()

    if content.lower().startswith("!incident"):
        description = content[len("!incident"):].strip()
        if not description:
            await message.reply("Please describe the incident. Usage: `!incident <description>`")
            return

        await handle_incident(message, description)

    elif content.lower().startswith("!status"):
        await message.reply("Runbook is online and ready. Use `!incident <description>` to report an issue.")

    elif content.lower().startswith("!memory"):
        await show_memory(message)


async def handle_incident(message, description):
    """Process an incident report through the AI pipeline."""
    # Acknowledge receipt
    thinking_msg = await message.reply(
        "🔍 **Incident received.** Running AI diagnostics...\n"
        f"```{description[:200]}```"
    )

    try:
        # Call backend to create and process incident
        async with aiohttp.ClientSession() as session:
            payload = {
                "description": description,
                "reporter": str(message.author),
                "source": "discord",
                "source_message_id": str(message.id),
                "source_channel_id": str(message.channel.id),
            }
            async with session.post(f"{BACKEND_URL}/api/incidents", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    await send_result(message, thinking_msg, result)
                else:
                    error_text = await resp.text()
                    await thinking_msg.edit(content=f"❌ Pipeline failed: {error_text[:200]}")
    except aiohttp.ClientError as e:
        await thinking_msg.edit(content=f"❌ Could not reach backend: {str(e)}")
    except Exception as e:
        await thinking_msg.edit(content=f"❌ Unexpected error: {str(e)}")


async def send_result(message, thinking_msg, result):
    """Format and send the pipeline result back to Discord."""
    diagnosis = result.get("diagnosis", {})
    remediation = result.get("remediation", {})
    ticket = result.get("ticket", {})
    pr = result.get("pull_request", {})

    severity_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }
    sev = result.get("severity", "medium")
    emoji = severity_emoji.get(sev, "🟡")

    response = (
        f"{emoji} **Incident Diagnosed** — `{result.get('title', 'Incident')}`\n\n"
        f"**Root Cause:** {diagnosis.get('root_cause', 'Unknown')}\n\n"
        f"**Suggested Fix:** {remediation.get('suggested_fix', 'Investigating...')}\n\n"
        f"**Immediate Actions:**\n"
    )

    actions = remediation.get("immediate_actions", [])
    for i, action in enumerate(actions[:5], 1):
        response += f"  {i}. {action}\n"

    response += f"\n📋 **Ticket:** {ticket.get('id', 'N/A')} — {ticket.get('title', '')}\n"
    response += f"🔀 **PR:** `{pr.get('branch', 'N/A')}` — {pr.get('title', '')}\n"

    customer_msg = remediation.get("customer_message", "")
    if customer_msg:
        response += f"\n💬 **Customer Update:** {customer_msg}\n"

    response += f"\n⏱️ **Est. Resolution:** {remediation.get('estimated_resolution_time', 'TBD')}"

    # Edit the thinking message with the result
    await thinking_msg.edit(content=response)


async def show_memory(message):
    """Show stored incident memories."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/dashboard/memory") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memories = data.get("memories", [])
                    if not memories:
                        await message.reply("📭 No past incidents in memory yet.")
                        return

                    response = "📚 **Incident Memory** (past resolutions):\n\n"
                    for mem in memories[:5]:
                        response += f"• **{mem['summary'][:80]}**\n"
                        response += f"  Root cause: {mem['root_cause'][:60]}\n"
                        response += f"  Fix: {mem['resolution'][:60]}\n\n"
                    await message.reply(response)
                else:
                    await message.reply("❌ Could not fetch memory.")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")


def main():
    if not DISCORD_BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not set in .env file")
        sys.exit(1)
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
