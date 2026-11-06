# Beginner's Guide — Running the Court of Inquiry Application

No Docker knowledge needed. Everything below is copy-paste.

**Important:** keep this `beginner-pack` folder *inside* the project folder
(the folder that contains `compose.yml`, usually `$HOME/legal/beginner-pack`).

---

## One-time setup (do once, takes 2 minutes)

Open **Terminal** and run:

```bash
bash beginner-pack/install-desktop-shortcut.sh
```

Optional — make it start by itself when you log in (no administrator needed):

```bash
bash beginner-pack/install-autostart.sh
```

## Everyday use

| You want to... | Do this |
| --- | --- |
| **Start / open the app** | Double-click the **Start Court of Inquiry** icon on the Desktop (or run `bash start-legal.sh`). The browser opens `http://localhost:8080`. |
| **Check if it is running** | Run `bash status-legal.sh` |
| **Stop it** | Run `bash stop-legal.sh` — nothing is deleted; cases, law data and the AI model all stay |
| **Log in** | The login is a placeholder (any username works) |

Run commands from the project folder, e.g.:

```bash
cd $HOME/legal
bash status-legal.sh
```

## If something goes wrong

| Message says | Meaning | What to do |
| --- | --- | --- |
| Docker is not running | The service is off | `sudo systemctl start docker` (or ask your administrator) |
| images are missing | The images were not loaded | Insert DVD 1, copy `legal-images.tar.gz` into `offline/images/`, run `bash start-legal.sh` again |
| model folder is missing | `offline/ollama` was not restored | Copy it from the DVD (setup.md section 5), run start again |
| did not become ready in time | Something is broken | Run `bash status-legal.sh` — it prints the last log lines; give those to whoever helps you |
| icon shows as text file | Not yet trusted | GNOME: right-click → *Allow Launching* · KDE: right-click → Properties → Permissions → *Is executable* |

The full error messages are friendly on purpose — read the two lines under
`!! PROBLEM:` first; they say exactly what is missing.

## Never do these (offline PC)

- Never run `ollama pull` or `docker pull` / `docker build` (there is no internet; compose is set to refuse them anyway).
- Never delete `backend/uploads` (your cases), `data/` (law documents) or `offline/ollama` (the AI model).
- Never run `docker system prune`.
- Do not expose the app to a network — it listens only on this computer (`localhost`), which is intentional.

## Getting this pack onto the offline PC

The six files in `beginner-pack` total under 100 KB. Put them on any spare
DVD/USB (whichever your security policy allows) and copy the folder into the
project folder (`$HOME/legal/beginner-pack`). That is all — the scripts need
no installation and no internet.

## Where things live

```
$HOME/legal/                     the project (code + compose files)
├── beginner-pack/               these helper scripts
├── backend/uploads/             your cases         <- back this up
├── data/                        law documents      <- back this up
└── offline/ollama/              the AI model       <- back this up
```
