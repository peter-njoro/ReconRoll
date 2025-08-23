# 👁️‍🗨️ FaceTrack Lite — Because Who Even Remembers Faces Anymore?

Welcome to **FaceTrack Lite** — the facial recognition attendance system you *didn't* ask for but will definitely flex on your portfolio anyway.

Because hey, **why remember a face** when you can just **slave your life away building a complex computer vision system** to do it for you? 😩

So you’re telling me… you *could* remember faces like a normal functioning human being?
Nah fam, let’s **build software that stalks—I mean, tracks—people's faces** for attendance instead.
Work smarter, not... human-er 🤖.

This project is part of a bigger thing called **Virone**, brainchild of the one and only [Everlyne Mwangi](https://github.com/everlyne-dotcom) (yes, that Everlyne — check her GitHub later in the repo). It’s just a small taste of what Virone aims to achieve.

---

## 💡 What Is This?

FaceTrack Lite is a ✨*lite*✨, *super chill* (and by chill we mean "I lost sleep building this") AI-powered facial recognition attendance system. For schools, events, or anywhere people show up (reluctantly or otherwise). It detects, recognizes, and tracks faces like it’s auditioning for *Black Mirror* Season 6.

Use it for:

* 👨‍🏫 Schools (because taking roll call is sooo 2001)
* 🎟️ Events (badge scanners are out, facial scans are in)
* 🧍 Flexing on LinkedIn (be honest)

---

## ⚙️ Tech Stack (a.k.a. My Red Flags)

| Tool                  | Why I Used It                                                                        |
| --------------------- | ------------------------------------------------------------------------------------ |
| `Python`  🐍          | Duh. I'm not a monster.                                                              |
| `OpenCV`    👁️       | Because staring at pixel arrays is a lifestyle.                                      |
| `face_recognition` 🎭 | Like OpenCV but with vibes and pre-trained models. Built on dlib, and dlib don’t lie |
| `Django`    🔥        | To give the illusion of structure.                                                   |
| `SQLite`     🪨       | Because we broke broke (but portable).                                               |
| `Bootstrap 5` 💅      | For that mid-tier “I tried” UI aesthetic                                             |
| `JavaScript` ☕        | Yeah, that’s still around                                                            |

> May or may not work on Windows without 19 dependencies and a small prayer.

---

## 🔥 Features (aka What I Cried Over)

* 👁️ Real-time face detection (yes, *real* real-time)
* 🧠 Facial recognition with `face_recognition` library
* 🧾 Logs attendance like a passive-aggressive teacher
* 📸 Captures unknown faces so you can stalk—I mean, investigate
* 🧊 Works offline, because we touch grass
* 🎨 Web dashboard (because CLI is so 2004)
* 🗂️ Admin dashboard (for The One Person in control)
* 📸 Face enrollment (yes, your face now lives in the Matrix)

---

## 📦 How to Run This Beast

### 🚀 Recommended: With Docker (a.k.a. The Way of the Lazy Genius)

If you want this thing running without sacrificing your sanity (especially you Windows users 🫵), use Docker.

1. Clone the repo:

   ```bash
   git clone https://github.com/peter-njoro/facetrack-lite.git
   cd facetrack-lite
   ```

2. Build the image (aka, watch text scroll like in The Matrix):

   ```bash
   docker compose build # only if you are in development
   ```

3. Start the containers (aka, let Docker babysit your dependencies):

   on windows:
   ```bash
   docker compose -f docker-compose.windows.yml up
   ```
   on linux (for legends and honestly works better😎)
   ```bash
   docker compose -f docker-compose.linux.yml up
   ```
   why do I have two docker compose files for windows and linux? well, it's because this beast requires specified hardware access (webcam) on both operating systems, and I use both😂💀

4. Visit the app at:

   ```
   http://localhost:8000
   ```

🎉 Congrats, you’re running FaceTrack Lite like a civilized person.

---

### 🛠️ Alternative: Without Docker (for the Nerdy Gooners)

If you hate yourself and want to spend hours debugging `pip install` errors, here’s how:

1. Clone this repo:

   ```bash
   git clone https://github.com/peter-njoro/facetrack-lite.git
   cd facetrack-lite/app
   ```

2. Create your virtual bubble:

   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows, you rebel
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations like a true Django disciple:

   ```bash
   python manage.py migrate
   ```

5. Fire up Django:

   ```bash
   python manage.py runserver
   ```

6. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and bask in your hard-earned suffering.

---

## 📷 How It Works (Simplified for Scroll-Happy Folks)

1. Camera turns on (consensually).
2. Face is detected.
3. Face is recognized (or silently judged).
4. Attendance is logged.
5. Everyone claps. 🎉

---

## 🗂️ Folder Structure (aka Where the Chaos Lives)

```bash
facetrack-lite/
├── app
│   ├── config/                         # Django project settings
│   ├── face_recognition_models/        # Pretrained models for detection
│   ├── manage.py                       # Django boss baby
│   ├── recognition/                    # Face recognition app
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── face_utils.py               # All the OpenCV/dlib sorcery
│   │   ├── forms.py
│   │   ├── main.py                     # The chaos engine
│   │   ├── models.py
│   │   ├── recognition_runner.py       # Orchestrates recognition
│   │   ├── static/recognition/         # CSS + JS + vibes
│   │   ├── templates/recognition/      # HTML templates
│   │   ├── test_loading.py
│   │   ├── test_opencv.py
│   │   ├── urls.py
│   │   ├── utils/                      # Small helpers
│   │   ├── video_utils.py
│   │   └── views.py
│   └── users/                          # Auth app (login/signup)
│       ├── admin.py
│       ├── forms.py
│       ├── models.py
│       ├── urls.py
│       └── views.py
├── docker-compose.yml                  # Docker babysitter config
├── Dockerfile                          # Instructions for your container overlord
├── LICENSE                             # Because lawyers
├── qodana.yaml                         # Linting/config for JetBrains enjoyers
├── README.md                           # This very scroll
├── requirements.txt                    # All the dependencies you’ll forget
└── scripts/scripts.sh                  # Script automation magic
```

---

## 🤝 Contributing

Want to contribute? Fork this repo, make your changes, and submit a pull request to the **development** branch.

(Or wait till I decide if I want a CONTRIBUTING.md file — whichever comes first.)

---

## 🚨 Disclaimer

This project is for **educational & demo purposes**.
Yes, there’s sarcasm in the code, in the UI, and in this README. Don’t panic — your data is safe, I literally can’t access it even if I wanted to.

Please don’t build Skynet with this. But if you do, at least star the repo first ⭐.

---

## 🫡 Author

Made by [Peter](https://github.com/peter-njoro) —
Professional overthinker, part-time wizard, and full-time developer (uses Arch btw 🗿).

Big thanks to **Everlyne Mwangi** for inspiring this as part of the bigger **Virone** project.

---

## ✨ Final Thoughts

Run it. Flex it. Show it off. Confuse your friends. Impress recruiters.
Whatever works 🤷.

Peace out ✌️
