# Notes for coding agents

Tim Martin's personal site, created from the al-folio v1.2 starter (Jekyll). Layouts, includes and styles come from the `al_folio_*` gems, not from this repository.

- `baseurl` in `_config.yml` is intentionally blank because the site is served from the root of its domain. The docs in `docs/` describe al-folio's demo repository, whose baseurl is `/al-folio`; that does not apply here.
- Content lives in `_pages/`, `_posts/`, `_projects/`, `_data/` and `assets/img/`. See `README.md` for the file map.
- `_data/cv.yml` feeds both the CV page (`al_folio_cv` gem) and the PDF (`bin/render_cv.py`, run by `.github/workflows/render-cv.yml`). RenderCV rejects the web-only `label` and `summary`, so the script maps them to `headline` and a "Profile" section. Otherwise use field names both understand: `degree` rather than `studyType`, and `label`/`details` entries in sections not titled "Skills" (that title switches the web page to name/keywords entries).
- Keep the phone number, home address and date of birth off the site.
- Preview with `docker compose up -d`, then open `http://localhost:8080`. Read build errors with `docker compose logs`. Jekyll restarts by itself when `_config.yml` changes.
- To change a theme file, copy it from the gem into `_layouts/`, `_includes/` or `_sass/` (see "local overrides" in `docs/ARCHITECTURE.md`).
