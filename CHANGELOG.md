# Changelog

## [2.0.1] — 2026-05-22

### Fixed
- `entreprise_search` : correction du crash `AttributeError: 'NoneType' object has no attribute 'keys'`
  quand l'API Pappers renvoie `"finances": null` explicitement.
  Correction dans `_fmt_base()` : `e.get("finances", {})` → `e.get("finances") or {}`

## [2.0.0] — 2026-05-21

### Added
- 3-source aggregation: API Recherche Entreprises + Pappers API v2 + BODACC DILA
- `entreprise_search`: multi-criteria filtering (département, NAF, category, qualifications)
- `entreprise_fiche_complete`: enriched profile with Pappers (health score, UBO, legal acts)
- `entreprise_finances`: multi-year balance sheet history with calculated ratios (net margin, debt/equity)
- `entreprise_bodacc`: official BODACC announcements with type filtering
- `entreprise_dirigeants`: directors + beneficial owners (UBO) with Pappers
- `entreprise_verifier`: SIREN/SIRET validation with full status
- Graceful fallback: Pappers → API Recherche when token absent or error
- `install.ps1`: Windows auto-installer (Python detection, deps, Claude Desktop config)
