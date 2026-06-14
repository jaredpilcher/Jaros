# Landing page — host it in ~2 minutes

`index.html` is a **single self-contained file**: no build step, no dependencies,
no framework. Edit it in any text editor; host it anywhere static files go.

## Customize first (2 small edits)

1. **Install line** — the page shows `pip install jaros`. That works once you've
   published to PyPI (see `launch/PRELAUNCH.md`, step 1). Until then, either publish
   first, or change the two `pip install jaros` spots to:
   `pip install git+https://github.com/jaredpilcher/Jaros.git`
2. **(Optional) Replay clip** — to swap the terminal mock for your real screen
   recording, find `<!-- REPLAY CLIP -->` in `index.html` and follow the one-line
   instruction there (drop in a `<video>` tag pointing at `replay.mp4`).

The repo URL (`github.com/jaredpilcher/Jaros`) is already wired into every button.

## Host it — pick one

### Option A — GitHub Pages (free, no account beyond GitHub)
1. In your repo, create a `docs/` folder and copy `index.html` into it
   (or push this `launch/site/` folder).
2. Repo → **Settings → Pages** → Source: *Deploy from a branch* → branch `main`,
   folder `/docs` → **Save**.
3. Live in ~1 min at `https://<you>.github.io/<repo>/`.
   *Custom domain?* Add it under Pages → Custom domain, and a `CNAME` DNS record.

### Option B — Netlify (drag-and-drop, free)
1. Go to app.netlify.com → **Add new site → Deploy manually**.
2. Drag the `launch/site/` folder (or just `index.html`) onto the drop zone.
3. Live instantly at a `*.netlify.app` URL; add a custom domain in Site settings.

### Option C — Vercel (free)
1. `npm i -g vercel` then `cd launch/site && vercel` (follow prompts), **or**
2. vercel.com → New Project → import the repo → set the root to `launch/site`.

### Option D — Cloudflare Pages / S3 / any static host
Upload `index.html` as the site root. That's the whole deploy.

## After it's live
- Put the URL in your blog posts (replace `YOUR-SITE`), your GitHub repo's
  "Website" field (repo → About → ⚙), your X bio, and the launch posts.
- Check it on your phone — the layout is responsive; confirm the hero and the
  terminal block read well on a narrow screen.
- Re-test the **Copy** button on the install line.

## What's intentionally NOT here
No analytics, cookies, or trackers (keeps it dependency-free and privacy-clean).
If you want basic traffic numbers, add a one-line privacy-friendly snippet
(Plausible/Fathom/Cloudflare Web Analytics) just before `</body>`.
