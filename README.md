# 🐝 AITKL2025 Hackathon – ASBhive Social Enterprise Mapping

## 🚀 Overview

AITKL2025 is an interactive web application built during the ASBhive Hackathon to solve a real-world problem faced by **ASBhive Malaysia**: the lack of a centralized, real-time database for social enterprises. The platform enables information extraction from public sources and offers a user-friendly interface to **list**, **showcase**, and **submit** social enterprise profiles.

---

## 🧩 Key Features

- **🔍 Company List Page**  
  View and filter all social enterprises based on criteria like location, sector, batch, and funding stage.

- **✨ Showcase Page**  
  Detailed view for each company, including:
  - Branding (logo, tagline, metadata)
  - Tags badge
  - About text
  - Interactive section navigation (Company, Jobs, News)
  - Founder profiles with LinkedIn links

- **📤 Submission Form**  
  Structured form allowing new companies to submit their profile, which integrates with the existing database.

---

## 🛠 Tech Stack

- **Backend**: Flask (Python)  
- **Frontend**: Tailwind CSS + Flowbite for styling and reusable UI components  
- **Data**: Stored in JSON files; display logic via Jinja templates  
- **Dev Tools**: npm, Tailwind CLI, virtualenv, GitHub (version control)

---

## 🎨 Design & Theme

We use ASBhive’s official color palette:
- **🔴 Primary**: `#b4173a`  
- **⚪ Secondary**: `#ffffff`  
- **🟦 Tertiary**: `#334f57`  

Consistent branding across components, badges, buttons, and navigation ensures strong visual identity.

---

## ⚙️ Installation & Setup

1. **Clone Project**
   ```bash
   git clone https://github.com/showherda/AITKL2025.git
   cd AITKL2025

2. **Python Setup**
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # Linux/macOS
    .\.venv\Scripts\activate    # Windows PowerShell
    pip install -r requirements.txt

3. **Install Frontend Dependencies**
    ```bash
    npm install

4. **Compile Tailwind CSS**
    ```bash
    npx tailwindcss -i ./static/src/input.css \
                -o ./static/dist/output.css \
                --watch

5. **Run Flask Server**
   ```bash
   python flask_app.py

6. **Visit http://127.0.0.1:5000/ in your browser.**

Install dependencies from the `pyproject.toml` by running, the below code in the main directory:

```
pip install .
```

Add .env file with `GEMINI_API_KEY`, the function is in `startup_analyzer.py`. 
To see how to use it, trying looking into `st_debug_app.py`

---

## 💡 Future Enhancements

- Full-text search & dynamic filtering using JavaScript
- Admin dashboard for data moderation
- External API integrations (Crunchbase, LinkedIn, etc.)
- Authentication & user roles (submitters, approvers)
- Export/import options (CSV, Excel)



