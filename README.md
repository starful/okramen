# ⛩️ JinjaMap (Tokyo Shrine Explorer)

**JinjaMap** is a web application that maps major shrines in Tokyo. It helps users discover power spots based on specific wishes (Wealth, Love, Health, etc.) using an interactive Google Map.

Unlike the previous version, this system now operates on a **static data build system** using Markdown files, ensuring faster performance and easier content management without external API dependencies.

## ✨ Features

*   **Markdown-Based Content**: Manage shrine data easily via local `.md` files in the `app/content/` directory.
*   **Automated Data Build**: The system automatically converts Markdown to JSON during the Docker build process.
*   **Google Maps Integration**: Visualizes shrine locations with custom markers and interactive info windows.
*   **Theme-Based Filtering**:
    *   💰 **Wealth** (재물)
    *   ❤️ **Love** (연애/사랑)
    *   💊 **Health** (건강)
    *   🎓 **Study** (학업)
    *   🛡️ **Safety** (안전)
*   **Responsive Design**: Fully optimized for mobile and desktop.
*   **Serverless Deployment**: Hosted on Google Cloud Run.

## 🛠️ Tech Stack

*   **Backend**: Python 3.10, Flask, Gunicorn
*   **Data Processing**: Python-frontmatter (Markdown parsing)
*   **Frontend**: HTML5, CSS3, Vanilla JS
*   **Infrastructure**: Docker, Google Cloud Run, Cloud Build

## 📂 Project Structure

```text
jinjaMap/
├── app/
│   ├── content/            # [CORE] Shrine data files (.md)
│   ├── static/             # Assets (CSS, JS, Images, JSON)
│   ├── templates/          # HTML Templates
│   └── __init__.py         # Flask App
│
├── build_data.py           # Script: Converts Markdown -> JSON
├── Dockerfile              # Container config (Runs build_data.py)
├── cloudbuild.yaml         # CI/CD config
└── requirements.txt        # Dependencies
```

## 📝 How to Add a New Shrine

1.  Create a new Markdown file in **`app/content/`** (e.g., `meiji_jingu.md`).
2.  Add the required **Frontmatter** at the top:

```yaml
---
layout: post
title: "Meiji Jingu Shrine"
date: 2024-03-20
categories: [love, peace]
tags: [Tokyo, PowerSpot]
thumbnail: /static/images/jinja/meiji.webp
lat: 35.6764
lng: 139.6993
address: 1-1 Yoyogikamizonocho, Shibuya City, Tokyo
excerpt: A brief summary of the shrine...
---

(Write the full description here using Markdown...)
```

3.  When you deploy, `build_data.py` will automatically include this file in the map data.

## 🚀 Deployment Guide

This project is deployed to **Google Cloud Run** using **Cloud Build**.

### 1. Prerequisites
*   Google Cloud SDK installed.
*   Project ID set: `starful-258005`

### 2. Deploy Command
Since external API keys are no longer needed for the build process, the command is simple:

```bash
gcloud builds submit
```

This command will:
1.  Upload the source code.
2.  Build the Docker image (and generate `shrines_data.json`).
3.  Deploy the new image to Cloud Run.

## ⚠️ Configuration

### Google Maps API Key
The Google Maps API key is client-side. Ensure `app/templates/index.html` contains a valid key with **HTTP Referrer restrictions** configured in the Google Cloud Console.

## 📝 License

This project is for educational and portfolio purposes.