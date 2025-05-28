# Xinyu & Qiujun - Love Anniversary Website

A Flask-based personal love anniversary website to record beautiful moments together. Updated on 2025-05-28.

## Features

- Track days since the beginning (December 10, 2022)
- 100-day milestone celebrations
- Beautiful photo gallery with fullscreen view
- Password protection

## Deploying to Vercel

1. Push code to GitHub repository
2. Connect GitHub repository in Vercel
3. Configure custom domain xinyu-qiujun.fun
4. Set up environment variables

## Environment Variables

Add the following environment variables in Vercel project settings:

- `PASSWORD`: Website access password
- `SECRET_KEY`: Flask session key

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` file and set environment variables
3. Run: `python app.py`
