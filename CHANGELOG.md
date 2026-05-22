# Changelog

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
- `config.json` token configuration (env var or file)

### Fixed (vs v1)
- `ModuleNotFoundError: mcp` — now documented in README with fix
- Multiple Python versions conflict — install.ps1 uses absolute path
- Missing `pydantic` after Python update — quick repair command documented

## [1.0.0] — Initial version

- Basic SIREN lookup
- Single API source
