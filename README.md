# 👁️‍🗨️ FaceTrack Lite — Because Who Even Remembers Faces Anymore?

Welcome to **FaceTrack Lite** — the facial recognition attendance system you *didn't* ask for but will definitely flex on your portfolio anyway.

Because hey, **why remember a face** when you can just **slave your life away building a complex computer vision system** to do it for you? 😩

So you’re telling me… you *could* remember faces like a normal functioning human being?  
Nah fam, let’s **build software that stalks—I mean, tracks—people's faces** for attendance instead.  
Work smarter, not... human-er 🤖.

“Caught wind of a pretty cool idea around ethical attendance systems 👀 — couldn’t help spinning up my own chaotic version. Totally unaffiliated (I swear 😅), but still down to collaborate if anyone’s building something similar 👋.”

---

## 💡 What Is This?

FaceTrack Lite is a ✨*lite*✨, *super chill* (and by chill we mean "I lost sleep building this") AI-powered facial recognition (attendance) system for schools, events, or anywhere people show up (reluctantly or otherwise). It detects, recognizes, and tracks faces like it's training for *Black Mirror* Season 6.

Use it for:
- 👨‍🏫 Schools (because taking roll call is sooo 2001)
- 🎟️ Events (badge scanners are out, facial scans are in)
- 🧍 Just flexing on LinkedIn (be honest)

---

## ⚙️ Tech Stack (a.k.a. My Red Flags)

| Tool         | Why I Used It                          |
|--------------|----------------------------------------|
| `Python`  🐍     | Duh. I'm not a monster.                |
| `OpenCV`    👁️   | Because staring at pixel arrays is a lifestyle. |
| `face_recognition` 🎭 | Like OpenCV but with vibes and pre-trained models. Built on dlib, and dlib don’t lie |
| `Django`    🔥   | To give the illusion of structure.     |
| `SQLite`     🪨  | Because we broke broke (but portable). |
| `Bootstrap 5` 💅 | For that mid-tier “I tried” UI aesthetic and also because HTML is for masochists. |
| `JavaScript` ☕ | Yeah, that’s still around |


> May or may not work on Windows without 19 dependencies and a small prayer.

---

## 🔥 Features (aka What I Cried Over)

- 👁️ Real-time face detection (yes, *real* real-time)
- 🧠 Facial recognition using the `face_recognition` library  
- 🧾 Logs attendance like a passive-aggressive teacher (so nobody can fake being “present” while on a coffee run)  
- 📸 Captures unknown faces so you can stalk—I mean, investigate  
- 🧊 Works offline, because we touch grass  
- 🎨 Comes with a web dashboard because CLI is so 2004
- 🗂️ Admin dashboard (for The One Person who controls everything)
- 📸 Face enrollment (yes, your face now lives in the Matrix)

---

## 📦 How to Run This Beast

1. Clone this repo like it's your crush’s Insta:
   ```bash
   git clone https://github.com/peter-njoro/facetrack-lite.git
  - Enter the matrix
    ```bash   
    cd facetrack-lite
2. Create your little virtual bubble:
   ```bash
   python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows, you rebel
3. Install the dependencies
   ```bash
   pip install -r requirements.txt
4. Fire up Django
   ```bash
   python manage.py runserver
(✨ and just like that, you’re a surveillance overlord)

## 📷 How It Works (Simplified Because You’re Probably Scrolling)
1. Camera turns on (consensually).
2. Face is detected.
3. Face is recognized (or judged silently).
4. Attendance is logged in the database.
5. Everyone claps. 🎉

## 🗂️ Folder Structure (Django + Face Recognition Edition)
```bash
facetrack-lite/
├── manage.py                                # The boss baby of Django
├── .gitignore                               # Because some files just don't deserve Git
├── README.md                                # The holy scroll (with ✨ sarcasm)
├── requirements.txt                         # A list of libraries you'll totally forget to pin
├── env/                                     # Your virtual env. Not in Git. Not in your business.
│
├── config/                                  # Django project settings folder
│   ├── __init__.py
│   ├── settings.py                          # Where you hardcode secrets until you regret it
│   ├── urls.py                              # URL jungle
│   ├── asgi.py
│   └── wsgi.py
│
├── recognition/                             # Your app for face detection and attendance
│   ├── __init__.py
│   ├── admin.py                             # Register models here if you're feeling spicy
│   ├── apps.py
│   ├── models.py                            # Tables that judge your life choices
│   ├── views.py                             # Where logic lives, breaks, and rises again
│   ├── forms.py                             # For the brave: custom forms
│   ├── urls.py                              # App-level URLs (so your main urls.py can breathe)
│   ├── face_utils.py                        # Where OpenCV/face_recognition sorcery lives
│   ├── attendance.py                        # Time tracking so your app can snitch who’s late
│   ├── templates/
│   │   └── recognition/
│   │       ├── index.html                   # Homepage — probably has buttons
│   │       ├── enroll.html                  # For registering new faces
│   │       └── attendance.html              # “Hello boss, here’s the attendance”
│   ├── static/
│   │   └── recognition/
│   │       ├── css/
│   │       │   └── styles.css               # Where the aesthetic vibes happen
│   │       ├── js/
│   │       │   └── main.js                  # Optional JS chaos
│   │       └── uploads/
│   │           └── faces/                   # Where face images chill
│   └── migrations/                          # Django does black magic here
│
└── db.sqlite3                               # Your default DB until you meet PostgreSQL

```
## 🚨 Disclaimer

This project is for **educational & demo purposes**.  
Please don't build Skynet and say it was my fault.  
Also: don't use this for evil. But if you do, at least star the repo first ⭐.

---

## 🫡 Author

Made by [Peter](https://github.com/peter-njoro) —  
Professional overthinker, part-time wizard, and full-time developer using Arch btw 🗿.

---

## ✨ Final Thoughts


Give it a spin. Flex it at school. Impress that recruiter. Scare your friends.  
Whatever works 🤷.

Peace out ✌️
