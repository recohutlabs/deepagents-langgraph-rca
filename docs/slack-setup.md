# Slack Setup

Slack is optional. Investigations run without Slack credentials.

To publish approved updates:

1. Create a Slack app.
2. Add bot scope `chat:write`.
3. Install the app to the workspace.
4. Invite the bot to the target channel.
5. Set:

   ```text
   SLACK_CHANNEL=#task-rca-demo
   SLACK_BOT_TOKEN=xoxb-...
   ```

The channel tool is guarded by a human-in-the-loop interrupt and duplicate-send prevention. Tests mock Slack and do not require credentials.
