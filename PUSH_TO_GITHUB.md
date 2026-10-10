# Push this project to GitHub

Repository: https://github.com/OthnyLight/in-hs-math-earlywarning

```bash
cd ~/Documents/in-hs-math-earlywarning
git init -b main
git add -A
git -c user.name="Othniel Iyassa Sa'anga" -c user.email="othnylight@gmail.com" commit -m "v0.1.0: Indiana HS early-warning model for first-year college outcomes"
git remote add origin https://github.com/OthnyLight/in-hs-math-earlywarning.git
git push -u origin main
```
If Git asks for a password, use a GitHub personal access token (GitHub → Settings → Developer settings → Personal access tokens → Fine-grained, Contents: read and write for this repository), or publish with GitHub Desktop (File → Add Local Repository → Publish).

Then: connect the repository in Zenodo (zenodo.org → Account → GitHub) and create release `v0.1.0` on GitHub to mint the DOI; turn on Pages (Settings → Pages → branch `main`, folder `/docs`) to serve the map at https://othnylight.github.io/in-hs-math-earlywarning/map/. See `docs/PUBLISH_GUIDE.md` for the rest.
