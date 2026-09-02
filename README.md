# 📓 Gemini Journal — Multimodal Reflective AI Companion

> A production-grade, secure journaling platform deployed serverless on **Google Cloud Run**, integrating **Google GenAI (`gemini-3.6-flash`)**, **Firebase Authentication**, **Google Cloud Firestore**, and **Google Secret Manager**.

[![Google Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-Deployed-4285F4?logo=google-cloud&logoColor=white)](https://gemini-journal-569758845707.asia-south1.run.app)
[![Gemini 3.6-Flash](https://img.shields.io/badge/Model-Gemini_3.6--Flash-8E75B2?logo=google)](https://ai.google.dev/)
[![Firestore Native](https://img.shields.io/badge/Database-Cloud_Firestore-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com/)
[![Secret Manager](https://img.shields.io/badge/Security-Google_Secret_Manager-34A853?logo=google-cloud&logoColor=white)](https://cloud.google.com/secret-manager)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🌐 Live Application
* **Production URL**: [https://gemini-journal-569758845707.asia-south1.run.app](https://gemini-journal-569758845707.asia-south1.run.app)
* **Cloud Run Region**: `asia-south1` (Mumbai)
* **Verification Label**: `dev-tutorial=cloud-run-ai-challenge`

---

## 💡 The Problem & The Solution

Traditional digital journals are passive text editors: they cannot interpret visual context, provide real-time emotional feedback, or process handwritten artifacts.

**Gemini Journal** bridges human introspection and multimodal AI:
* **Bimodal Input**: Users can write prompts, dictate thoughts, or attach photos of sketches, handwritten notes, whiteboards, and real-life scenes.
* **Contextual Vision Processing**: Images are processed directly with the user prompt using `gemini-3.6-flash`, allowing visual notes to receive analytical and emotional reflection.
* **Serverless Elasticity**: Deployed on Google Cloud Run with automatic scaling to zero to minimize idle resource consumption.
* **Strict Privacy Isolation**: Every reflection is encrypted and keyed exclusively to the user's verified Firebase identity.

---

## 🌟 Core Features

| Feature | Description |
| :--- | :--- |
| 📷 **Multimodal Vision** | Attach handwritten notes, daily photos, or sketches; Gemini analyzes both image contents and textual prompts in a single inference call. |
| 🎭 **Adaptive Personas** | Switch between Empathetic (compassionate), Socratic (introspective inquiry), Stoic (resilience & control), and Action-Oriented (concrete tasks). |
| 📊 **Automated Sentiment Analytics** | Automatically tags entries with dominant emotional states (`happy`, `sad`, `anxious`, `reflective`, `neutral`) to monitor mental wellness over time. |
| 🔥 **Daily Streak Tracking** | Encourages consistent reflective habits through a daily streak tracker synced to Cloud Firestore. |
| 🔒 **Enterprise Secrets Architecture** | Zero credentials in the frontend or source code; all API keys are resolved at runtime via Google Secret Manager. |

---

## 🏗️ System Architecture

```text
[ Browser / Frontend Client ]
       │
       │  • HTML5 / CSS3 / Vanilla JS
       │  • Firebase Client SDK (OAuth Token Generation)
       │  • Base64 Image Compression & Encoding
       ▼
[ Google Cloud Run (asia-south1) ]
       │
       │  • Python Flask App running under Gunicorn
       │  • Firebase Admin SDK (Decodes and verifies Bearer Tokens)
       │  • Google Secret Manager (Dynamic GOOGLE_API_KEY resolution)
       ▼
[ External Managed Google Services ]
       ├── Cloud Firestore  ──► Stores per-user logs under /users/{uid}/entries
       └── Google GenAI SDK ──► gemini-3.6-flash multimodal prompt + image pipeline