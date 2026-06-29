# 🦘 TourDesk AI

> A guest message classifier for Turtle Down Under, powered by our own TDU web chatbot.  
> Guests start a conversation in the in-app chatbot; incoming messages are automatically routed into **Automated**, **Assisted**, or **Escalate** tiers using a fine-tuned DistilBERT model — with a live dashboard to monitor everything.

---

## 📁 Repository Structure

```
tourdesk/
├── backend/
│   ├── app.py                  # Flask entry point
│   ├── routes/
│   │   ├── chat.py             # Chatbot page + /api/chat endpoint
│   │   ├── dashboard.py        # Serves the HTML frontend
│   │   └── api.py              # JSON API for the dashboard
│   └── utils/
│       ├── classifier.py       # Loads DistilBERT, exposes predict()
│       ├── message_store.py    # In-memory message store
│       └── chat.py             # Chatbot reply builders
├── frontend/
│   ├── templates/
│   │   ├── dashboard.html      # Staff dashboard page
│   │   └── chat.html           # Guest chatbot widget
│   └── static/
│       ├── css/style.css
│       ├── css/chat.css
│       ├── js/dashboard.js     # Polling, feed rendering, test panel
│       └── js/chat.js          # Guest chatbot logic
├── ml_classifier/
│   ├── preparingTrainingData.ipynb
│   ├── trainModel.ipynb
│   ├── predict.py              # CLI prediction script
│   ├── requirements.txt        # ML-only dependencies
│   ├── sample_messages.csv     # 10 test messages
│   └── model/                  # ← Download from Google Drive (not in repo)
├── docs/
│   └── TourDesk_AI_Model_Report.docx
├── requirements.txt            # Full app dependencies
├── .env.example                # Environment variable template
└── README.md
```

---

## 🖥️ How It Works

```
Guest opens the TDU web chatbot  (/chat)
        │
        ▼
Chatbot widget (chat.js)
        │  POST /api/chat
        ▼
Flask Backend (app.py)
        │
        ▼
DistilBERT Classifier
        │
   ┌────┴────────────────┐
   │                     │
Automated            Assisted / Escalate
   │                     │
Auto-reply sent      Appears in dashboard
back in the chat     (Escalate also flagged for staff)
```

---

## 🚀 Setup on Your Work Desktop (Windows, `C:\Users\cucum`)

Follow every step in order the **first time**. After that, daily use is just Steps 6–7.

---

### Step 1 — Check Prerequisites

Open **PowerShell** and run:

```powershell
python --version   # need 3.10+
git --version
pip --version
```

If anything is missing:

| Tool | Link |
|------|------|
| Python 3.11 | https://www.python.org/downloads/ — ✅ tick "Add to PATH" |
| Git | https://git-scm.com/download/win |

---

### Step 2 — Clone the Repo

```powershell
cd C:\Users\cucum\Documents
git clone https://github.com/JoeyHanma69/tourdesk.git
cd tourdesk
```

---

### Step 3 — Create & Activate Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> ⚠️ If activation is blocked, run this once then retry:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

You should now see `(venv)` at the start of the prompt.

---

### Step 4 — Install Dependencies

```powershell
pip install -r requirements.txt
```

> ⏱️ First install: 5–10 min. PyTorch is ~800 MB.

---

### Step 5 — Set Up Environment Variables

```powershell
copy .env.example .env
notepad .env
```

Fill in the values in Notepad:

```env
SECRET_KEY=any-random-string-here
MODEL_DIR=ml_classifier/model
CONFIDENCE_THRESHOLD=0.65
```

Save and close. No external messaging credentials are needed — the chatbot is hosted by this app.

---

### Step 6 — Download the Trained Model from Google Drive

The model is too large for GitHub. Download it from your Drive:

1. Open Google Drive → navigate to `TDU_youmom/tourdesk_distilbert/`
2. Right-click the folder → **Download** (saves as `.zip`)
3. Extract it so the files land at:

```
tourdesk\ml_classifier\model\
    config.json
    model.safetensors
    tokenizer.json
    tokenizer_config.json
    special_tokens_map.json
    vocab.txt
```

---

### Step 7 — Run the App

```powershell
# Make sure venv is active and you're in the project root
cd C:\Users\cucum\Documents\tourdesk
.\venv\Scripts\Activate.ps1

python backend/app.py
```

You should see:
```
✅ Classifier loaded from ml_classifier/model
🚀 TourDesk AI running on http://localhost:5000
```

Open your browser:

- **Staff dashboard:** http://localhost:5000
- **Guest chatbot:** http://localhost:5000/chat

The dashboard shows the live message feed, stats, and the test panel. The chatbot is what guests use to start a conversation — every message they send is classified and appears in the dashboard feed.

---

### Step 8 — Try the Chatbot

1. Open **http://localhost:5000/chat** (or click **💬 Open Chat** in the dashboard header).
2. The assistant greets you and starts the conversation.
3. Type a message and send — you'll get an automated reply, and the message appears live in the staff dashboard.

That's the whole loop — no external services, tunnels, or webhooks required.

---

## 🔁 Daily Workflow (After Initial Setup)

Every time you come back to work on this:

```powershell
cd C:\Users\cucum\Documents\tourdesk
.\venv\Scripts\Activate.ps1
python backend/app.py
```

Then open http://localhost:5000 (dashboard) and http://localhost:5000/chat (chatbot) in your browser.

---

## 🧪 Quick Test

Use the **Test Classifier** panel on the dashboard — type any message and click **Classify** — or just chat with the bot at `/chat`.

Or use the CLI:

```powershell
python ml_classifier/predict.py --message "What time does the tour start?"

# Batch test
python ml_classifier/predict.py --file ml_classifier/sample_messages.csv --output results.csv
```

---

## 📤 Pushing Changes to GitHub

```powershell
git add .
git commit -m "describe your change"
git push origin main
```

First push on a new machine needs a Personal Access Token:
1. https://github.com/settings/tokens → Generate new token (classic) → tick `repo`
2. Use it as your password when Git prompts

---

## 🔄 Retraining the Model (When You Have More Labelled Data)

Do this in **Google Colab**, not locally:

1. Open https://colab.research.google.com
2. Upload `ml_classifier/trainModel.ipynb`
3. **Runtime → Change runtime type → T4 GPU**
4. Update `LABELLED_CSV` in Cell 4 to your updated CSV path in Drive
5. Run all cells — Cell 1 auto-restarts (normal)
6. New model saves back to Drive automatically
7. Re-download to `ml_classifier/model/` on your desktop

---

## 📊 Model Performance

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| Automated | 0.87 | 0.95 | **0.91** | 58 |
| Assisted  | 0.71 | 0.56 | **0.62** | 9  |
| Escalate  | 0.90 | 0.69 | **0.78** | 13 |
| **Macro Avg** | 0.83 | 0.73 | **0.77** | 80 |

Overall accuracy: **86.3%** · Training set: **533 labelled messages** · Model: `distilbert-base-uncased`

---

## ❓ Troubleshooting

**`ModuleNotFoundError: No module named 'flask'`**
→ Run `.\venv\Scripts\Activate.ps1` first.

**Dashboard shows "Stub Mode — model not loaded"**
→ Model files are missing. Re-check Step 6 — `model.safetensors` must be in `ml_classifier/model/`.

**Chatbot page won't load at `/chat`**
→ Make sure the Flask server is running on port 5000. Open http://localhost:5000/chat directly.

**`error: src refspec main does not match any`** on first push
→ `git branch -M main` then `git push -u origin main`

**Activation script blocked**
→ `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## 📬 Contact

Built by Joey Linao — Software Developer Intern, Turtle Down Under.
