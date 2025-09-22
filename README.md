# FaceTrack Lite

**FaceTrack Lite** is a lightweight facial recognition attendance system built with **Django** and **OpenCV**. It allows schools, events, and organizations to automate attendance tracking by detecting, recognizing, and logging faces in real time.

This project is part of a larger initiative called **Virone**, originally envisioned by [Everlyne Mwangi](https://github.com/everlyne-dotcom). FaceTrack Lite is a demonstration of the potential within that broader vision.

---

## Overview

FaceTrack Lite provides:

* Real-time face detection and recognition
* Attendance logging and reporting
* Capture of unidentified faces for later review
* Admin and web dashboards for easy management
* Offline functionality

It is designed to be portable, lightweight, and suitable for demos, small-scale deployments, and educational purposes.

---

## Tech Stack

| Tool               | Purpose                                     |
| ------------------ | ------------------------------------------- |
| `Python`           | Core language for development               |
| `OpenCV`           | Computer vision and image processing        |
| `face_recognition` | Facial recognition powered by dlib          |
| `Django`           | Web framework for structure and scalability |
| `SQLite`           | Lightweight, portable database              |
| `Bootstrap 5`      | Frontend styling                            |
| `JavaScript`       | Client-side interactivity                   |

---

## Features

* Real-time face detection
* Facial recognition with pre-trained models
* Automated attendance logging
* Capture of unknown faces for later review
* Admin and web dashboards
* Face enrollment system
* Offline support

---

## Installation & Setup

Before running the project, please review the **[Pre-Installation Guide](https://docs.google.com/document/d/1OgYudT0YOkN6vht0wn9dWe4mxkAFOjGnz5ulX36hd94/edit?usp=sharing)**.

### Run with Docker (recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/peter-njoro/facetrack-lite.git
   cd facetrack-lite
   ```

2. Build the image:

   ```bash
   docker compose build
   ```

3. Start the containers:

   ```bash
   # For Linux
   docker compose -f docker-compose.linux.yml up

   # For Windows
   docker compose -f docker-compose.windows.yml up
   ```

4. Access the app at:

   ```
   http://localhost:8000
   ```

### Run without Docker (manual setup)

1. Clone the repository:

   ```bash
   git clone https://github.com/peter-njoro/facetrack-lite.git
   cd facetrack-lite
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run database migrations:

   ```bash
   python manage.py migrate
   ```

5. Start the server:

   ```bash
   python manage.py runserver
   ```

6. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## How It Works

1. Camera captures input.
2. Face is detected.
3. Face is recognized or marked as unknown.
4. Attendance is logged automatically.

---

## Project Structure

```bash
facetrack-lite/
├── config/                  # Django project settings
├── recognition/             # Face recognition app
│   ├── face_utils.py        # OpenCV/dlib logic
│   ├── models.py            # Database models
│   ├── views.py             # Django views
│   ├── templates/           # HTML templates
│   └── static/              # CSS & JS
├── docker-compose.yml        # Docker configuration
├── Dockerfile                # Docker build instructions
├── requirements.txt          # Dependencies
└── README.md                 # This document
```

---

## Contributing

Contributions are welcome!

* Fork the repo
* Create a feature branch
* Submit a pull request to the **development** branch

---

## Disclaimer

This project is for **educational and demo purposes only**.
It is not production-ready and should not be used in sensitive or large-scale deployments without further development and security hardening.

---

## Author

Developed by [Peter](https://github.com/peter-njoro).
Special thanks to [Everlyne Mwangi](https://github.com/everlyne-dotcom) for inspiring the project as part of the larger **Virone** vision.

---

## Developer Notes

If you’ve scrolled this far — welcome to the part where I sneak in my personality:

* Yes, I cried over `pip install` errors.
* Docker was supposed to save my sanity, but webcams had other plans.
* This project is both a demo and a flex. Use responsibly.
* I may or may not use Arch Linux 🟟o.
* If this ends up running Skynet… at least
