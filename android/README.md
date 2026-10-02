# AI Live Quiz Engine — Android (V1)

Kotlin + Jetpack Compose client for the FastAPI backend. Matches every
endpoint in `backend/app/api/` field-for-field.

## Opening the project

1. Android Studio → **Open** → select this `android/` folder.
2. Studio will detect there's no Gradle wrapper checked in and offer to
   generate one automatically — accept that (or run
   `gradle wrapper --gradle-version 8.9` yourself if you have Gradle
   installed locally). This repo intentionally ships without the binary
   `gradle-wrapper.jar` so it stays a plain source tree.
3. Let Gradle sync. First sync will download AGP 8.6.0 / Kotlin 2.0.21 /
   Compose BOM 2024.09.02 — needs an internet connection to
   `dl.google.com` and `repo.maven.apache.org`.

## Pointing it at your backend

Edit `BASE_URL` in
`app/src/main/java/com/ailivequiz/app/data/network/RetrofitInstance.kt`:

- **Emulator** (default): `http://10.0.2.2:8000/` — this is the
  emulator's special alias for your machine's `localhost`. No change
  needed if you're running `uvicorn` on the same machine as Android
  Studio.
- **Physical device**: replace with your machine's LAN IP, e.g.
  `http://192.168.1.42:8000/`. Your phone and computer must be on the
  same Wi-Fi network, and you must start the backend with
  `uvicorn app.main:app --host 0.0.0.0 --port 8000` (not the default
  `--reload`-only invocation, which binds to `127.0.0.1`).

`android:usesCleartextTraffic="true"` is already set in the manifest so
plain HTTP works for local dev. Remove it once the backend is deployed
behind HTTPS.

## What's implemented (V1 scope)

- **Library screen** — lists uploaded PDFs, upload button opens the
  system file picker restricted to `application/pdf`.
- **Quiz config screen** — pick question count (1–20), triggers
  `POST /quizzes/generate`.
- **Quiz screen** — one card per question, radio-button options, submit
  disabled until every question is answered.
- **Result screen** — score, percentage, and a per-question review with
  correct/incorrect icons and the AI's explanation text.
- **History screen** — past attempts via `GET /attempts/user/{id}`.

There's no login screen yet — `AppViewModel` silently creates/reuses a
single demo user (`student@ailivequiz.local`) via `POST /users/` on
launch. Swap that for a real auth flow in V2; no other screen needs to
change since they all just read `userId` from the ViewModel.

## Known V1 simplifications (documented, not bugs)

- Single hardcoded demo user, no login UI.
- No offline caching (Room) yet — every screen hits the network live.
- No retry/backoff on failed requests — errors surface as text and the
  user has to tap again.
- Quiz question order isn't shuffled — comes back in whatever order the
  AI/backend returns.

These match what the proposal scopes for V2+ (offline support, auth,
etc.), so leaving them out of V1 is intentional, not an oversight.
