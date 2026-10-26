# Tim Martin – personal website

Source of my personal website (about, CV, projects, blog), built with the [al-folio](https://github.com/alshedivat/al-folio) v1.2 Jekyll starter.

## Preview locally

```bash
docker compose up -d   # first run downloads the image (~1 GB)
# open http://localhost:8080 – the site rebuilds when files change
docker compose logs -f # build output and errors
docker compose down
```

## Where things live

| What                          | File                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| Name, URL, site-wide settings | `_config.yml`                                                        |
| Home page text and photo      | `_pages/about.md`, `assets/img/prof_pic.jpg`                         |
| CV (web page and PDF)         | `_data/cv.yml`                                                       |
| Social links                  | `_data/socials.yml`                                                  |
| Blog posts                    | `_posts/YYYY-MM-DD-title.md` (start from `_drafts/post-template.md`) |
| Projects                      | `_projects/*.md` (start from `_projects/project-template.md`)        |
| GitHub cards                  | `_data/repositories.yml`                                             |

## Publishing

Pushing to `main` runs `.github/workflows/deploy.yml`, which builds the site into the `gh-pages` branch that GitHub Pages serves.
Changes to `_data/cv.yml` also run `render-cv.yml`, which rebuilds the PDF in `assets/rendercv/rendercv_output/` and commits it.

al-folio's own documentation is in `docs/`. It describes the al-folio demo repository, so ignore its advice about a `/al-folio` baseurl: this site is served from the root of its domain.
