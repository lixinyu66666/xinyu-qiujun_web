# Xinyu & Qiujun - Love Anniversary Website

A Flask-based personal love anniversary website to record beautiful moments together. Updated on May 30, 2025.

## Features

* Track days since the beginning (December 10, 2022)
* 100-day milestone celebrations
* Beautiful photo gallery with fullscreen view
* Journal system to record memories with MongoDB
* Photo storage with MongoDB GridFS or Local Storage
* Password protection
* Modular codebase structure
* Vercel deployment support

## Important Note: Vercel Deployment Issue Workaround

### Root Cause

Vercel is a **stateless service platform** that does not allow server-side persistent file writes. When you try to add logs, the server attempts to write to the `journal.json` file, which is not permitted in the Vercel environment, resulting in a 500 Internal Server Error.

### Solution 1: Use MongoDB Database for Journal Entries

The application has been updated to support MongoDB. You can set it up as follows:

1. Sign up and log in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a free-tier database cluster.
3. In the Security settings, add a username and password.
4. In Network Access, allow access from any address (add `0.0.0.0/0`).
5. Obtain the connection string, formatted like:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/mydb?retryWrites=true&w=majority
   ```
   
### Solution 2: Use MongoDB GridFS for Image Storage

The application now uses MongoDB GridFS for image storage, replacing Firebase Storage. This approach is:

1. Free to use with your MongoDB Atlas account
2. Integrated with the existing MongoDB database
3. Efficient for storing and retrieving binary data like images
4. Compatible with Vercel's stateless deployment model

To enable GridFS storage, update your `.env` file with:
   ```
   USE_GRIDFS_STORAGE=true
   ```

## Deploying to Vercel

1. Push code to your GitHub repository.
2. Connect the GitHub repository in Vercel.
3. Configure the custom domain `xinyu-qiujun.fun`.
4. Set up environment variables (see below).

## Environment Variables

In your Vercel project settings, add the following environment variables:

* `PASSWORD`: The password for accessing the site.
* `SECRET_KEY`: Flask session secret key.
* `MONGODB_URI`: MongoDB Atlas connection string.
* `MONGODB_DB`: Database name (e.g., `journal_db`).
* `USE_GRIDFS_STORAGE`: Set to `true` to use MongoDB GridFS for image storage.
* `VERCEL`: Set to `1`.

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file and set environment variables:
   ```
   SECRET_KEY=your_random_secret_key
   PASSWORD=your_password
   # MongoDB configuration
   MONGODB_URI=your_mongodb_connection_string
   MONGODB_DB=journal_db
   # Storage configuration
   USE_GRIDFS_STORAGE=true
   ```
3. Run: `python app.py`
4. Open [http://localhost:8080](http://localhost:8080/) in your browser.

## Troubleshooting

If you still encounter errors on Vercel:

1. Check the Vercel deployment logs.
2. Verify that the MongoDB connection string is correct.
3. Confirm that all environment variables are set correctly.
4. Redeploy the project from GitHub.
