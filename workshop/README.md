# Showroom-Style Workshop Source

The workshop now contains two Antora modules:

- `documentation/modules/ARCHITECTURE/` is the primary architecture-aligned learning path covering framework planning, deployment modes, operators, Day-2 operations, validation, reporting, troubleshooting, and component extension.
- `documentation/modules/ROOT/` retains the original Redfish and Assisted Installer workshop as proven source material and a focused Day-0 learning track.

The original standalone Markdown workshop remains available at `../WORKSHOP.md`. It is intentionally preserved and should not be removed without migration evidence and equivalent coverage.

Build the workshop with:

```bash
antora default-site.yml
```
