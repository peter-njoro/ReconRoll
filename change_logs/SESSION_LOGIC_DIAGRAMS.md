# Session Logic - Visual Diagrams & Decision Trees

## 1. Complete Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRODUCTION FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

CLIENT (Windows/Any OS)                    BACKEND (Linux Server)
┌──────────────────────┐                  ┌─────────────────────────────────┐
│  Webcam Frame        │                  │  Django + Recognition Engine    │
│  30 FPS stream       │                  │                                 │
└──────────────────────┘                  │  views.py:upload_frame()        │
         │                                │  ├─ Decode frame               │
         │ POST /api/upload_frame/        │  ├─ Queue to frame_queue       │
         ├───────────────────────────────→│  └─ Return fast response       │
         │                                │                                 │
         │                                │  recognition_runner.py         │
         │                                │  ├─ Load session               │
         │                                │  ├─ Load known encodings       │
         │   (Meanwhile, background)      │  │  (session scoped!) ✅ FIX #1 │
         │                                │  ├─ Get frame from queue       │
         │                                │  ├─ Detect faces               │
         │                                │  ├─ Match against known        │
         │                                │  ├─ Process unknowns           │
         │                                │  └─ Update database            │
         │                                │                                 │
         │   Long polling for status      │  Models:                       │
         ├─────────────────────────────→│  ├─ AttendanceRecord ✅ scoped│
         │                                │  ├─ UnidentifiedFace ✅ scoped│
         │                                │  ├─ Event ✅ scoped           │
         │                                │  └─ Session ✅ scoped         │
         │ ← - - - - - - - - - - - - - ←│                                 │
         │  status + counts               │                                 │
         │                                └─────────────────────────────────┘
```

---

## 2. Face Recognition Decision Tree

```
                    FACE DETECTED IN FRAME
                            │
                ┌───────────┴───────────┐
                │                       │
    ┌───────────▼──────────┐  ┌────────▼─────────┐
    │  Get face encoding   │  │  Get face        │
    │  (128-d vector)      │  │  locations       │
    │                      │  │  (bounding boxes)│
    └───────────┬──────────┘  └────────┬─────────┘
                │                      │
                ├──────────┬───────────┤
                           │
            ┌──────────────▼─────────────────┐
            │  matches_face_encoding()       │
            │                                │
            │  encoding:        known_faces │
            │  [128-d vector]   from DB     │
            │          │                     │
            │  Calculate L2 distance         │
            │  to each known encoding        │
            │                                │
            └──────────────┬─────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        ┌───────▼────────┐    ┌───────▼────────┐
        │ distance       │    │ distance       │
        │ < 0.55?        │    │ >= 0.55?       │
        └───────┬────────┘    └───────┬────────┘
                │ YES                 │ NO
        ┌───────▼─────────┐   ┌───────▼──────────────┐
        │ KNOWN STUDENT ✅│   │ Check unknown_cache  │
        │                 │   │ (in-memory)          │
        │ name: "John"    │   │                      │
        │ is_known: True  │   └───────┬──────────────┘
        │ idx: 0          │           │
        └───────┬─────────┘   ┌───────┴─────────┐
                │             │                 │
        ┌───────▼──────────┐  │ Found match?   │
        │ Create           │  │                 │
        │ AttendanceRecord │  └────┬────────┬──┘
        │ (session,        │       │ YES    │ NO
        │  student=John)   │       │        │
        │                  │   ┌───▼──┐  ┌──▼────┐
        │ ✅ Updated to    │   │DUPE  │  │BRAND  │
        │    session.      │   │UNKN. │  │NEW    │
        │    attendance    │   │      │  │UNKN.  │
        │    _records      │   │Skip  │  │       │
        │                  │   │      │  │idx:-1 │
        └──────────────────┘   └──┬───┘  └──┬────┘
                                  │         │
                             ┌────┘         └────┐
                             │                   │
                    ┌────────▼─────────┐    ┌────▼──────────┐
                    │ Log "duplicate"  │    │ save_          │
                    │                  │    │ unidentified   │
                    │ Skip processing  │    │ _faces()       │
                    └──────────────────┘    │                │
                                            ├─ Save images  │
                                            │  (cropped +    │
                                            │   full frame)  │
                                            │                │
                                            ├─ Create        │
                                            │  Unidentified  │
                                            │  Face record   │
                                            │  ✅ scoped to  │
                                            │     session    │
                                            │                │
                                            ├─ Add encoding  │
                                            │  to memory     │
                                            │  cache         │
                                            │  (prevent      │
                                            │   future dups) │
                                            │                │
                                            └────────────────┘
```

---

## 3. Database Transaction Flow

```
SESSION CS101 RUNNING
───────────────────────────────────────────────────────────────

Frame 1: John's face detected
│
├─ Query: load_known_encodings_from_db(session=session) ✅ SCOPED
│  └─ Session.class_group = CS101
│  └─ Load only [John, Jane, Bob] encodings
│  └─ DB Query: ClassGroup.students.all() → 3 students
│
├─ Compare: face_enc vs [John_enc, Jane_enc, Bob_enc]
│  └─ Best match: John_enc at distance 0.38
│
├─ is_known=True, name="John Smith"
│  
├─ Query: Student.objects.filter(full_name="John Smith").first()
│
├─ Create: AttendanceRecord(
│     session=session_cs101,    ← Linked to THIS session ✅
│     student=john_obj
│  )
│  └─ Unique constraint: (session, student) prevents duplicate
│
└─ Create: Event(
     session=session_cs101,     ← Linked to THIS session ✅
     student=john_obj,
     event_type='face_recognized'
  )

─────────────────────────────────────────────────────────────

Frame 2: Same unknown person
│
├─ Query: load_known_encodings_from_db(session=session) ✅ SCOPED
│  └─ Same as before: [John, Jane, Bob]
│
├─ Compare: face_enc vs [John_enc, Jane_enc, Bob_enc]
│  └─ No match (distance > 0.55)
│
├─ Compare: face_enc vs unknown_encodings (in-memory) ✅ SESSION SCOPED
│  └─ Best match: unknown_enc[0] at distance 0.12
│
├─ is_known=False, idx=0 (not -1, so not brand new)
│
└─ Log: "Unknown face already saved, skipping duplicate"
   └─ No database writes ✅ Efficient

─────────────────────────────────────────────────────────────

Frame 3: Alice (from MATH session)
│
├─ Query: load_known_encodings_from_db(session=session) ✅ SCOPED
│  └─ Still only: [John, Jane, Bob] (Alice NOT included)
│
├─ Compare: alice_enc vs [John_enc, Jane_enc, Bob_enc]
│  └─ No match (Alice not in CS101 class)
│
├─ Compare: alice_enc vs unknown_encodings (in-memory)
│  └─ No match (different person from Frame 2 unknown)
│
├─ is_known=False, idx=-1 (BRAND NEW)
│
├─ Query: save_unidentified_faces(...)
│  └─ Save to disk: /media/uploads/unidentified/...
│
├─ Create: UnidentifiedFace(
│     session=session_cs101,    ← Linked to THIS session ✅
│     cropped_face=path1,
│     full_frame=path2
│  )
│
├─ Create: Event(
│     session=session_cs101,    ← Linked to THIS session ✅
│     event_type='unknown_face'
│  )
│
└─ Add: unknown_encodings.append(alice_enc) ✅ SESSION CACHE

─────────────────────────────────────────────────────────────

Session Ends:
│
├─ Update: Session.status = 'ended'
├─ Update: Session.end_time = now()
├─ Create: Event(
     session=session_cs101,    ← Linked to THIS session ✅
     message='1 recognized, 2 unknown'
  )
│
└─ Final counts:
   ├─ session.attendance_records.count() = 1
   ├─ session.unidentified_faces.count() = 2
   └─ session.events.count() = 5

```

---

## 4. Multi-Session Concurrency

```
CONCURRENT SESSIONS - ZERO CONTAMINATION
═════════════════════════════════════════════════════════════════

Session A (CS101)              Session B (MATH202)
─────────────────              ──────────────────
ClassGroup: CS101              ClassGroup: MATH202
Students: [John, Jane, Bob]    Students: [Alice, Charlie]

Thread A:                      Thread B:
┌──────────────────┐          ┌──────────────────┐
│ Frame queue A    │          │ Frame queue B    │
│ ↓ frame_A_1     │          │ ↓ frame_B_1     │
│ ↓ frame_A_2     │          │ ↓ frame_B_2     │
└──────────────────┘          └──────────────────┘
         │                            │
         │                            │
    ┌────▼─────────────┐      ┌──────▼────────────┐
    │ load_known_      │      │ load_known_       │
    │ encodings        │      │ encodings         │
    │ (session=A)      │      │ (session=B)       │
    │                  │      │                   │
    │ Encodings:       │      │ Encodings:        │
    │ [John,Jane,Bob]  │      │ [Alice,Charlie]   │
    │ Size: 3×128-d    │      │ Size: 2×128-d     │
    └────┬─────────────┘      └──────┬────────────┘
         │                            │
    ┌────▼──────────┐          ┌──────▼──────────┐
    │ unknown_      │          │ unknown_        │
    │ encodings[] A │          │ encodings[] B   │
    │ (empty)       │          │ (empty)         │
    │ ← Session scoped!         │ ← Session scoped!
    └────┬──────────┘          └──────┬──────────┘
         │                            │
    Frame A1: John detected     Frame B1: Alice detected
         │                            │
    ┌────▼──────────────┐        ┌────▼───────────────┐
    │ Match John in A's  │        │ Match Alice in B's │
    │ encodings         │        │ encodings         │
    │ ✅ Found          │        │ ✅ Found          │
    │                  │        │                   │
    │ Create:          │        │ Create:           │
    │ AttendanceRecord │        │ AttendanceRecord  │
    │ (session=A,      │        │ (session=B,       │
    │  student=John)   │        │  student=Alice)   │
    │                  │        │                   │
    │ ✅ Separate      │        │ ✅ Separate       │
    │    database      │        │    database       │
    │    records!      │        │    records!       │
    └───────────────────┘        └────────────────────┘
         │                            │
         ├─ No contamination ✅      ├─ No contamination ✅
         └─ Session A: 1 present     └─ Session B: 1 present
```

---

## 5. Encoding Comparison (L2 Distance)

```
FACE ENCODING COMPARISON
═══════════════════════════════════════════════════════════════

Each face is represented as a 128-dimensional vector:
[0.45, 0.82, -0.12, ..., 0.33]  ← 128 numbers

Comparison:
Known John:  [0.45, 0.82, -0.12, ..., 0.33]
Detected:    [0.48, 0.80, -0.11, ..., 0.34]
             
             Distance = √((0.48-0.45)² + (0.80-0.82)² + ... + (0.34-0.33)²)
                      = √(0.0009 + 0.0004 + ... + 0.0001)
                      = 0.38

DISTANCE INTERPRETATION:
─────────────────────────

Distance  Meaning
0.0 - 0.2 ✅ Definitely same person
0.2 - 0.45 ✅ Likely same person
0.45 - 0.55 ⚠️ Edge case (threshold area)
0.55 - 0.7 ❌ Different person (probably)
0.7 - 1.0+ ❌ Definitely different person

DEFAULT THRESHOLD: 0.55
└─ Distances < 0.55 → Match found
└─ Distances ≥ 0.55 → No match

TUNING:
┌─ TOLERANCE = 0.45
│  └─ Stricter: fewer false positives, more false negatives
│     (Miss some valid students)
│
├─ TOLERANCE = 0.55 (DEFAULT)
│  └─ Balanced: good accuracy
│
└─ TOLERANCE = 0.65
   └─ Looser: more false positives, fewer false negatives
      (Mark wrong students as present)
```

---

## 6. Database Schema - Session Update Flow

```
┌──────────────────────────────────────────────────────────────┐
│                         DATABASE                              │
└──────────────────────────────────────────────────────────────┘

Session Table:
┌────────┬──────────┬─────────────┬───────────┐
│ id     │ subject  │ class_group │ status    │
├────────┼──────────┼─────────────┼───────────┤
│ sess-1 │ CS101    │ cg-1        │ ongoing   │ ← This session
│ sess-2 │ MATH202  │ cg-2        │ ongoing   │
└────────┴──────────┴─────────────┴───────────┘
           │                         │
           └─────────┬───────────────┘
                     │
                     ▼
            load_known_encodings_from_db(session=sess-1)
                     │
                     ├─ Gets session.class_group = cg-1
                     │
                     ▼
            ClassGroup.students.all()
                     │
            ┌────────┴────────┬───────────┐
            │                 │           │
            ▼                 ▼           ▼
      ┌─────────┐        ┌─────────┐  ┌─────────┐
      │ Student │        │ Student │  │ Student │
      │ John    │        │ Jane    │  │ Bob     │
      │ id: s1  │        │ id: s2  │  │ id: s3  │
      └────┬────┘        └────┬────┘  └────┬────┘
           │                  │            │
           ├─ Has encodings ──┼────────────┤
           │                  │            │
           ▼                  ▼            ▼
      ┌────────────┐    ┌────────────┐  ┌────────────┐
      │ FaceEncoding
      │ path: ...  │    │ FaceEncoding
      │            │    │ path: ...  │  │ FaceEncoding
      │            │    │            │  │ path: ...  │
      └────────────┘    └────────────┘  └────────────┘
           │                  │            │
           └──────────┬───────┴────────────┘
                      │
              Load numpy arrays:
              - john_enc:  128-d vector
              - jane_enc:  128-d vector
              - bob_enc:   128-d vector
                      │
                      ▼
      ┌──────────────────────────────────┐
      │ known_face_encodings = np.array  │
      │ [[john_enc], [jane_enc], [bob]] │
      │                                  │
      │ known_face_names = ["John",     │
      │                     "Jane",     │
      │                     "Bob"]      │
      └──────────────────────────────────┘
                      │
              Used for matching:
              distances = L2_norm(known_face_encodings - detected_enc)
                      │
                      ▼
      ┌──────────────────────────────────┐
      │ Best match: John at distance 0.38│
      │ is_known=True                    │
      └──────────────────────────────────┘
                      │
                      ▼
      AttendanceRecord Table:
      ┌────────┬─────────┬──────────┐
      │ session│ student │ timestamp│
      ├────────┼─────────┼──────────┤
      │ sess-1 │ s1(John)│ 14:30:25 │ ← Created here
      └────────┴─────────┴──────────┘
                      │
                      ▼
      Event Table:
      ┌────────┬──────────────────┬──────────┐
      │ session│ event_type       │ timestamp│
      ├────────┼──────────────────┼──────────┤
      │ sess-1 │ face_recognized  │ 14:30:25 │ ← Created here
      │ sess-1 │ unknown_face     │ 14:35:42 │
      └────────┴──────────────────┴──────────┘
```

---

## 7. Time Sequence Diagram

```
TIME    CLIENT              DJANGO HTTP            recognition_runner
────    ──────              ────────────            ──────────────────
00:00   Start webcam
        30 FPS stream
        ↓

00:00                       Start session
                            create Session(
                              id='s1',
                              class_group=CS101
                            )
                                                    Start recognition_runner
                                                    Load session 's1'
                                                    ↓
00:01   Frame 1 ──────→    upload_frame(img)      Load known_encodings
        [John face]        ├─ Decode              (session=s1)
                           ├─ Queue frame         ├─ Load [John,Jane,Bob]
                           └─ Return 200 OK       ├─ Process frame 1
                           ↑ ~35ms                ├─ Match: John
                                                  ├─ Create
                                                  │ AttendanceRecord
                           
00:02   Frame 2 ──────→    upload_frame(img)      ├─ Process frame 2
        [Jane face]        ├─ Decode              ├─ Match: Jane
                           ├─ Queue frame         ├─ Create
                           └─ Return 200 OK       │ AttendanceRecord
                           ↑ ~35ms
                                                  
00:03   Frame 3 ──────→    upload_frame(img)      ├─ Process frame 3
        [Alice face]       ├─ Decode              ├─ No match
        (from MATH)        ├─ Queue frame         │  (Alice not in CS101)
                           └─ Return 200 OK       ├─ Save as unknown
                           ↑ ~35ms                ├─ Create
                                                  │ UnidentifiedFace

00:04                                             Every 500 frames:
                                                  Reload known_encodings
                                                  (picks up new students)

00:30   Stop session ──→   end_session(s1)        Session ended
        (manual)           ├─ Update status       ├─ Finalize stats
                           │ = 'ended'            ├─ Close cleanly
                           └─ Redirect            └─ Log summary

TOTAL LATENCY:
│ Upload: ~10ms
│ Queue: <1ms
│ Frame decode: ~10ms
│ Queue response: ~15ms
├─ HTTP RESPONSE: ~35ms ✅
│
│ Background processing:
│ Load: <1ms (cached)
│ Detect: ~30ms
│ Encode: ~80ms (num_jitters=2)
│ Match: <1ms
│ DB write: ~5ms
└─ BACKGROUND PROCESS: ~120ms (async) ✅
```

---

## Summary: The Fix in One Image

```
BEFORE FIX (❌ WRONG):
───────────────────────────────────────
Student.objects.all()  ← Query ALL students
         │
         ├─ CS101: [John, Jane, Bob]
         ├─ MATH: [Alice, Charlie]     ← WRONG! Loaded for CS101 too
         ├─ BIO: [Dave, Eve]           ← WRONG! Loaded for CS101 too
         └─ etc...
         │
         ▼
If Alice appears in CS101 session:
  └─ ❌ MATCHED → Marked as present in CS101
  └─ ❌ WRONG SESSION

AFTER FIX (✅ CORRECT):
───────────────────────────────────────
session.class_group.students.all()  ← Query ONLY this class
         │
         ├─ CS101: [John, Jane, Bob]
         └─ That's it!  ✅
         │
         ▼
If Alice appears in CS101 session:
  └─ ✅ NOT MATCHED → Marked as unknown
  └─ ✅ CORRECT BEHAVIOR
```

