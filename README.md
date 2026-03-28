# 🍜 OKRamen - Discover Japan's Best Ramen Shops & Local Gems

**OKRamen** is a global interactive map platform designed to help travelers find the soul of Japanese food—Ramen. Beyond a simple list, OKRamen offers deep-dive guides powered by AI and an intuitive filtering system based on broth types and culinary styles.

🔗 **Live Demo:** [https://okramen.net](https://okramen.net)

---

## ✨ Key Features

*   **Interactive Ramen Map**: Explore curated ramen shops across Japan using the **Google Maps JavaScript API** with **Advanced Markers** and a custom **Map ID**.
*   **Global Flavor Filtering**: Instantly filter shops by 7 primary world-class categories:
    *   🐷 **Tonkotsu** (Creamy Pork Broth)
    *   🥣 **Shoyu** (Classic Soy Sauce)
    *   🍲 **Miso** (Rich Soybean Paste)
    *   🧂 **Shio** (Light & Clear Salt)
    *   🐔 **Chicken** (Velvety Tori-Paitan)
    *   🥢 **Tsukemen** (Dipping Style Noodles)
    *   🥬 **Vegan** (Plant-based Varieties)
*   **Smart Multi-Language Mapping**: A unique logic that bridges the language gap. Clicking the English filter `Tonkotsu` automatically retrieves matching Korean data `돈코츠` for a seamless global experience.
*   **AI-Powered Deep Dive Guides**: Utilizes **Google Gemini 1.5** to generate 7,000+ character SEO-optimized articles covering shop history, broth complexity, and ordering tips.
*   **Performance First**: No traditional database required. Markdown files are compiled into a lightweight JSON cache, ensuring ultra-fast loading times via **Flask-Compress**.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.10, Flask, Gunicorn
*   **Frontend**: Vanilla JavaScript (ESM), Google Maps API (Advanced Markers)
*   **Content Management**: Markdown with YAML Frontmatter
*   **AI Integration**: Google Gemini 1.5 API (via `google-genai`)
*   **Image Processing**: Automated resizing/compression via Pillow
*   **Infrastructure**: Docker, Google Cloud Run, Cloud Build, Artifact Registry

---

## 🤖 Automation Scripts

This project includes powerful Python scripts to automate content operations:

1.  **`script/ramen_generator.py`**: Reads CSV master lists and uses Gemini AI to generate bilingual (EN/KO) Markdown content automatically.
2.  **`script/build_data.py`**: Compiles individual `.md` files into a production-ready `ramen_data.json` while cleaning up unnecessary AI tags (e.g., `## yaml` or code blocks).
3.  **`script/optimize_images.py`**: Compresses high-resolution images into web-optimized JPEGs (800px width, 75% quality).

---

## 🚀 Getting Started

### 1. Installation
```bash
git clone https://github.com/starful/okramen.git
cd okramen
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the root directory and add your API keys:
```env
GEMINI_API_KEY=your_google_gemini_api_key
```

### 3. Build & Run
```bash
# Compile Markdown files to JSON
python script/build_data.py

# Start the Flask server
python app/__init__.py
```
Visit `http://localhost:8080` in your browser.

---

## 📂 Project Structure

```text
okramen/
├── app/
│   ├── content/                 # AI Generated Markdown (.md)
│   ├── static/
│   │   ├── css/                 # Custom Ramen UI Theme
│   │   ├── js/                  # Filtering & Map Engine (main.js)
│   │   └── json/                # Compiled Production JSON Data
│   ├── templates/               # HTML Layouts (index, detail, etc.)
│   └── __init__.py              # Flask App Configuration
├── script/
│   ├── csv/                     # Master Shop Lists (ramens.csv)
│   ├── build_data.py            # Data Compiler & Cleaner
│   └── ramen_generator.py       # Gemini AI Content Bot
├── Dockerfile                   # Containerization
└── cloudbuild.yaml              # CI/CD Pipeline for GCP
```

---

## 🛡️ License

© 2026 OKRamen Project. All rights reserved.
Finding the legendary bowl of Ramen across Japan.
