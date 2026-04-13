# HKBU Chatbot - Telegram Intelligent Assistant

A Telegram-based intelligent chatbot designed for HKBU students, featuring AI conversations, course queries, image-to-video generation, and document analysis. Built with Docker microservices architecture for high concurrency and elastic scaling.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Educational-orange)](LICENSE)

---

## 📖 Table of Contents

- [Project Overview](#-project-overview)
  - [What Developers Built](#-what-developers-built)
  - [What Users Can Do](#-what-users-can-do)
- [Quick Start](#-quick-start)
- [Technical Architecture](#-technical-architecture)
- [Deployment Guide](#-deployment-guide)
- [FAQ](#-faq)

---

## 👥 Project Overview

### 👨‍💻 What Developers Built

#### 1. Core Architecture Design 🏗️
- **Microservices Architecture**: Bot Agent + Redis + Video Workers (3 replicas) + OCR Workers (3 replicas)
- **Async I/O**: Non-blocking processing using `asyncio` + `httpx.AsyncClient` + `asyncpg`
- **Task Queue**: Celery + Redis distributed task processing system
- **Containerization**: Docker + Docker Compose one-click deployment
- **Elastic Scaling**: Workers can be dynamically scaled for high concurrency

#### 2. AI Integration 🤖
- **ChatGPT Conversations**:
  - Dual async/sync mode support
  - Intelligent context understanding
  - Customized course assistant role
  - 60-second timeout protection
- **Image Analysis**:
  - AI automatic image content analysis
  - Smart recommendation of 3 animation prompts
  - Support for quick selection or custom input

#### 3. Image-to-Video Feature 🎬
- **SiliconFlow API Integration**:
  - Support for multiple image formats (JPG, PNG, GIF, WebP)
  - Base64 encoding transmission
  - Real-time status tracking (queued, processing, completed)
  - 50-minute timeout protection
- **Background Processing**:
  - Non-blocking video generation
  - Users can continue chatting
  - Automatic push when completed

#### 4. PDF Document Analysis 📄
- **Text Extraction**:
  - Fast extraction using PyMuPDF (fitz)
  - Support for first 5 pages
  - No OCR required, fast processing
- **AI Smart Summary**:
  - Core course objectives
  - Key deadlines/tasks
  - Important requirements/knowledge points

#### 5. Database Integration 💾
- **PostgreSQL**:
  - Async connection pool (asyncpg)
  - Course information storage
  - Chat log recording
  - Video generation records
- **Redis**:
  - Task queue broker
  - Result storage backend
  - Data persistence

#### 6. Error Handling & Logging 📝
- **Complete Logging System**:
  - All conversation records
  - Image analysis records
  - Video generation records (success/failure)
  - Detailed error logs
- **Graceful Degradation**:
  - API timeout retry
  - Detailed error messages
  - Automatic resource cleanup

#### 7. Performance Optimization ⚡
- **Connection Reuse**: HTTP client reuse, database connection pooling
- **Resource Limits**: CPU limits (0.5-2 cores), memory limits (512M-2G)
- **Timeout Configuration**: ChatGPT API (60s), document analysis (180s), video generation (3000s)

---

### 👤 What Users Can Do

#### 1. Smart Conversations 💬
**How to Use**: Simply send text messages

```
You: Hello
Bot: Hello! I'm the HKBU course assistant. I can help you query course information...

You: Tell me about cloud computing
Bot: Cloud computing is a service model that provides computing resources via the internet...
```

**Features**:
- ✅ Natural language understanding
- ✅ Context memory
- ✅ Friendly student assistant role

---

#### 2. Course Queries 📚
**How to Use**: Send messages containing course codes (format: 4 letters + 4 digits)

```
You: When is COMP7940 class?
Bot: According to database, COMP7940 (Cloud Computing) class time is
     Monday 14:00-17:00, Location: AAB101

You: What assignments does COMP7940 have?
Bot: COMP7940 assignments:
     - Assignment 1 (Deadline: 2026-04-20)
       Requirement: Implement Docker containerization
     - Final Project (Deadline: 2026-06-10)
       Requirement: Build microservices architecture application
```

**Features**:
- ✅ Automatic course code recognition
- ✅ Query class time and location
- ✅ View assignment deadlines
- ✅ Get course requirements

---

#### 3. Image-to-Video 🎬
**How to Use**: Send `/video` command, then upload an image

```
Step 1: Send /video
Bot: 🎬 Image to Video Mode
     Step 1: Please send me an image
     Send your image now!

Step 2: Upload image
Bot: ✅ Image received!
     🤖 AI Analysis: This is a beach sunset photo...
     
     Suggested prompts:
     1. Smooth zoom effect from wide to close-up
     2. Pan left to right showcasing the coastline
     3. Wave motion effect for added realism
     
     💡 Quick select: Send 1, 2, or 3
     ✏️ Or type your own custom prompt

Step 3: Select prompt or enter custom
You: 1

Bot: 🎬 Video generation started!
     ✅ Your video is being processed in the background.
     💬 You can continue chatting with me while waiting.

[2-10 minutes later]
Bot: ⏳ Your video is queued (Position: 2)
Bot: 🎬 Your video is being processed...
Bot: ✅ Video generated! Uploading...
Bot: [Sends video] 🎥 Your generated video is ready!
```

**Features**:
- ✅ AI automatic image analysis
- ✅ Smart animation effect recommendations
- ✅ Support for custom prompts
- ✅ Background processing, non-blocking
- ✅ Real-time status updates

**Supported Image Formats**: JPG/JPEG, PNG, GIF, WebP

---

#### 4. PDF Document Analysis 📄
**How to Use**: Simply send a PDF file

```
Step 1: Upload PDF file
Bot: 📄 Document Analysis
     ⏳ Downloading PDF...

Bot: 📄 Document Analysis
     ✅ PDF downloaded
     📖 Extracting text...
     🤖 Generating AI summary...

Step 2: View analysis results
Bot: 📝 **Document Analysis Result**
     📄 File: COMP7940_Syllabus.pdf
     
     Core Course Objectives:
     - Understand cloud computing fundamentals and architecture
     - Master Docker containerization technology
     - Learn microservices design patterns
     - Practice CI/CD automation deployment
     
     Key Deadlines/Tasks:
     - Assignment 1: 2026-04-20 (Docker deployment)
     - Midterm Exam: 2026-05-15
     - Final Project: 2026-06-10 (Microservices application)
     
     Important Requirements:
     - Attendance: 80% or above
     - Group project: 3-4 people
     - Programming language: Python, Docker
     - Cloud platform: AWS/Azure
```

**Features**:
- ✅ Automatic text extraction (first 5 pages)
- ✅ AI smart summary
- ✅ Identify key information
- ✅ Quick document understanding

**Notes**:
- ⚠️ PDF files only
- ⚠️ No image OCR support
- ⏱️ Processing time: ~1-2 minutes

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- Required API Keys (see below)

### 5-Minute Quick Deployment

```bash
# 1. Clone or extract the project
cd comp7940-lab

# 2. Configure API Keys
cp config.ini.example config.ini
# Edit config.ini and fill in your API keys

# 3. Start services
docker-compose up -d

# 4. View logs
docker-compose logs -f
```

That's it! Your bot is now running.

### Required API Keys

1. **Telegram Bot Token** - Get from [@BotFather](https://t.me/botfather)
2. **Azure OpenAI API** - For ChatGPT functionality
3. **SiliconFlow API** - For image-to-video generation
4. **PostgreSQL Database** (Optional) - For course information storage

See `config.ini.example` for detailed configuration instructions.

---

## 🏗️ Technical Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  Docker Container Architecture           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │ Telegram Bot │────────▶│    Redis     │             │
│  │  (chatbot_   │  Submit │  (Message    │             │
│  │   agent.py)  │  Tasks  │   Queue)     │             │
│  └──────────────┘         └──────┬───────┘             │
│         │                        │                      │
│         │                        │ Distribute Tasks     │
│         │                        │                      │
│         │               ┌────────┴────────┐            │
│         │               │                 │             │
│         │        ┌──────▼──────┐   ┌─────▼──────┐     │
│         │        │Video Worker │   │OCR Worker  │     │
│         │        │  (x3 replicas)│  │(x3 replicas)│    │
│         │        │             │   │            │     │
│         │        └──────┬──────┘   └─────┬──────┘     │
│         │               │                 │             │
│         └───────────────┴─────────────────┘             │
│                    Shared temp directory                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Python 3.12
- **Framework**: python-telegram-bot, Celery
- **Database**: PostgreSQL (asyncpg), Redis
- **HTTP**: httpx (async/sync)
- **Container**: Docker, Docker Compose
- **AI**: Azure OpenAI, SiliconFlow

### Project Structure

```
comp7940-lab/
├── chatbot_agent.py          # Bot main program (async)
├── ChatGPT_HKBU.py          # ChatGPT client (async/sync)
├── image_to_video.py        # Video generator
├── tasks.py                 # Celery task definitions
├── worker.py                # Worker entry point
├── docker-compose.yml       # Container orchestration
├── Dockerfile               # Image definition
├── requirements.txt         # Dependencies
├── README.md               # This document
└── DEPLOYMENT.md           # Detailed deployment guide
```

---

## 📦 Deployment Guide

### Local Deployment

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

### EC2 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed steps.

**Quick Steps**:
1. Prepare EC2 instance (recommended: t3.large, 8GB memory)
2. Install Docker and Docker Compose
3. Upload project files
4. Configure `config.ini`
5. Run `docker-compose up -d`

### Scale Workers

```bash
# Increase video workers to 5
docker-compose up -d --scale video_worker=5

# Increase OCR workers to 5
docker-compose up -d --scale ocr_worker=5
```

---

## 🔍 FAQ

### Q: How long does video generation take?
**A:** Usually 2-10 minutes, maximum up to 50 minutes (depending on API queue).

### Q: How to change the bot's reply style?
**A:** Edit `self.system_message` in `ChatGPT_HKBU.py`.

### Q: Is the database required?
**A:** No. Without a database, the bot can still chat and generate videos, but cannot query course information.

### Q: How to view logs?
**A:** 
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f bot
docker-compose logs -f video_worker
```

### Q: How to backup data?
**A:**
```bash
# Backup Redis data
docker-compose exec redis redis-cli SAVE

# Backup configuration
cp config.ini config.ini.backup
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for more questions.

---

## 📊 Performance Metrics

### Resource Usage

| Service | Replicas | CPU | Memory |
|---------|----------|-----|--------|
| Bot | 1 | 0.5 | 512M |
| Redis | 1 | 0.5 | 256M |
| Video Worker | 3 | 2 | 2G |
| OCR Worker | 3 | 1 | 1G |
| **Total** | **8** | **10** | **3.5G** |

### Concurrency Capacity

- **Conversations**: Unlimited (async processing)
- **Video Generation**: 3 concurrent
- **Document Analysis**: 3 concurrent

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

## 📄 License

This project is for educational and research purposes only.

---

## 📞 Contact

For questions, see [DEPLOYMENT.md](DEPLOYMENT.md) or submit an Issue.

---

**Made with ❤️ for HKBU Students**
