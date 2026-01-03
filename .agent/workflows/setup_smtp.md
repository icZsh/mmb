---
description: How to set up SMTP credentials for email notifications
---

# Setting up SMTP (Gmail)

The default configuration is set up for Gmail. To use it securely, you need to generate an App Password.

## 1. Enable 2-Step Verification
1. Go to your [Google Account Security settings](https://myaccount.google.com/security).
2. Under "How you sign in to Google", enable **2-Step Verification** if not already enabled.

## 2. Generate an App Password
1. Go to the [App Passwords page](https://myaccount.google.com/apppasswords).
   - If the link doesn't work, search for "App passwords" in the security page search bar.
2. Create a new app password:
   - **App name**: `Morning Market Briefing` (or any name you prefer)
   - Click **Create**.
3. Copy the 16-character password generated (spaces are optional/ignored).

## 3. Configure Local Environment
1. Copy `.env.example` to `.env` if you haven't already:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env`:
   - `SMTP_USER`: Your full Gmail address (e.g., `user@gmail.com`)
   - `SMTP_PASSWORD`: The 16-character App Password you just generated.

## 4. Configure GitHub Actions (for automated runs)
1. Go to your GitHub repository.
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret** for each variable:
   - Name: `SMTP_USER`, Secret: Your Gmail address
   - Name: `SMTP_PASSWORD`, Secret: Your App Password
   - Name: `EMAIL_RECIPIENT`, Secret: The email address to receive the briefing
   - (Optional) `SMTP_SERVER` and `SMTP_PORT` if using something other than default Gmail.

## Using Other Providers
If using a provider other than Gmail (e.g., Outlook, AWS SES, SendGrid):
1. Find their SMTP settings (Server, Port, Authentication method).
2. Update `SMTP_SERVER` and `SMTP_PORT` in your `.env` and GitHub Secrets accordingly.
