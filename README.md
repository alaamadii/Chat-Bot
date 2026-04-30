# NextTech AI Support Bot

### 📹 Output Demo

<video src="photo/video.mp4" width="100%" controls></video>

A comprehensive, modular customer service chatbot framework for NextTech. This project is designed to handle intelligent AI replies via Gemini, human agent handoffs, webhook integrations, and analytics tracking.

## 🚀 Features
- **Intake**: Normalizes inputs from multiple channels (WhatsApp, Web Chat).
- **AI Brain**: Uses Gemini API to understand intent, generate responses, and determine confidence.
- **Actions**: Handles business logic, human handoffs, and external integrations.
- **Delivery**: Safely formats messages back to specific channels.
- **Analytics**: Logs conversations and updates the dashboard.

## 🛠️ Setup Instructions

### 1. Python Environment Setup
Create a dedicated virtual environment for this project to keep dependencies clean:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and add your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## 🎮 How to Run

### Interactive Terminal Mode
Chat with the bot directly in your IDE console:
```bash
python chat.py
```

### Automated Test Pipeline
Run a simulated test of the entire pipeline (Intake -> Analytics):
```bash
python test_pipeline.py
```

### FastAPI Webhook Server
Start the background server to accept real incoming messages:
```bash
uvicorn intake.main:app --reload
```
*Note: The bot does not have a visual homepage. If you visit `http://127.0.0.1:8000` you will get a 404 error. Instead, visit the interactive testing dashboard at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** to test the bot from your browser!*

## 📱 Testing on a Real Device

If you want to test the bot from your phone (e.g., via a WhatsApp webhook or a web frontend), your device needs a way to communicate with your local computer.

We recommend using **Ngrok** to securely expose your local server to the internet.

### Step-by-Step Ngrok Guide
1. Start your local FastAPI server: `uvicorn intake.main:app --reload`
2. Download and install [Ngrok](https://ngrok.com/).
3. Open a new terminal and run:
   ```bash
   ngrok http 8000
   ```
4. Ngrok will provide a public URL that looks like this: `https://a1b2-c3d4.ngrok-free.app`
5. **WhatsApp (Meta/Twilio)**: Go to your developer console and paste this URL into the **Webhook URL** field (append `/webhook/whatsapp` at the end).
6. Now, whenever you text your bot's number from your phone, WhatsApp will forward the message to your local server!

## Alaa Madi ##
