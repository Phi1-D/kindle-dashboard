# Family Kindle dashboard

A GitHub Actions job builds a 600×800 greyscale image every 30 minutes. It shows the weather, sunrise and sunset, the family iCloud calendar, chores, a Christmas countdown and a daily fact. The jailbroken Kindle downloads and displays it.

```
iCloud calendar ─┐
Open-Meteo ──────┼─> GitHub Actions (every 30 min) ─> GitHub Pages image ─> Kindle
chores.txt ──────┘        ▲
                          └── iPhone Shortcut copies the "Chores" note into chores.txt
```

## 1. GitHub repo (about 15 minutes)

1. Create a new **public** repository called `kindle-dashboard`. Free GitHub Pages requires a public repo; see the privacy note below.
2. Upload every file in this folder, keeping the folder structure. The `.github/workflows/build.yml` file must go in exactly that path.
3. In **Settings → Pages**, set **Source** to **GitHub Actions**.
4. In **Settings → Secrets and variables → Actions**, add two secrets:
   - `ICAL_URL`: the shared calendar's public link. On iPhone, open Calendar, tap the calendar's ⓘ, turn on **Public Calendar** and copy the `webcal://…` link. Paste it as is.
   - `IMAGE_NAME`: a random string, e.g. `dash-7f3k92qx`. This keeps the image's address unguessable.
5. Go to **Actions → Build Kindle dashboard → Run workflow**. Once it's green, open
   `https://YOUR-USERNAME.github.io/kindle-dashboard/YOUR-IMAGE-NAME.png` in a browser to check it.

## 2. Chores from Apple Notes (iPhone Shortcut)

Apple Notes has no API, so an iPhone Shortcut pushes the note's text into `chores.txt` each morning, and the dashboard reads that.

First, create a **fine-grained personal access token** on GitHub under **Settings → Developer settings → Fine-grained tokens**. Limit it to the `kindle-dashboard` repo only, with the permission **Contents: Read and write**.

Then build a Shortcut called "Push chores" with these actions:
1. **Find Notes** where Name is `Chores`, limited to 1.
2. **Get Text from Input**, using the note.
3. **Base64 Encode** that text.
4. **Get Contents of URL**: `https://api.github.com/repos/YOUR-USERNAME/kindle-dashboard/contents/chores.txt`
   - Method GET. Headers: `Authorization` = `Bearer YOUR-TOKEN`, `Accept` = `application/vnd.github+json`
5. **Get Dictionary Value** `sha` from the result.
6. **Get Contents of URL**: the same URL, method **PUT**, with the same headers and a JSON request body:
   - `message` (text) = `Update chores`
   - `content` (text) = the Base64 result from step 3
   - `sha` (text) = the value from step 5

Finally, in **Automation → Personal → Time of Day**, set it to 06:30 daily, choose **Run Immediately**, and select "Push chores".

Each push also triggers a fresh dashboard build. Notes:
- Ticked checklist items probably still come through as plain text, so delete done items rather than ticking them. Test this.
- **Simpler alternative:** skip the Shortcut and edit `chores.txt` in the GitHub mobile app.

## 3. Kindle side

1. Jailbreak with WinterBreak (kindlemodding.org). No KUAL or hotfix is needed; current guides treat those as legacy.
2. Edit `kindle/dashboard.sh`: set `URL` to `https://phi1-d.github.io/kindle-dashboard/<IMAGE_NAME>.png`.
3. Copy `dashboard.sh` into the Kindle's `documents` folder. It appears in the Library as **Start Dashboard**.
4. Plug the Kindle into USB power, turn Wi-Fi on, and tap **Start Dashboard**.
5. **To stop it:** hold the power button for about 40 seconds. The Kindle restarts into its normal interface.

A log is written to `dashboard/dashboard.log` on the Kindle drive, which is useful if the screen stays blank.

## Privacy

- The calendar link lives only in a GitHub secret. It is never in the code and never public.
- The **rendered image is public** at an unguessable address. That's obscurity, not security: anyone with the link can see the day's events. Keep sensitive detail out of calendar titles, or pay for a GitHub plan that allows private Pages.
- `chores.txt` is visible in the public repo.

## Customising

- Location: `LAT`, `LON` in `dashboard/fetch.py`
- Facts: `dashboard/facts.txt`, one per line
- Layout: `dashboard/render.py`. Preview it locally with `python dashboard/main.py --sample`, which writes `public/dash.png`.
