# SBOM (Software Bill of Materials)

Generated using [Syft](https://github.com/anchore/syft) from the backend Python dependencies.

## Generate

```bash
# Install syft
brew install syft  # macOS
# or: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Generate CycloneDX SBOM for backend
syft dir:backend/ -o cyclonedx-json > security/sbom/backend-sbom.cdx.json

# Or from the built image
docker compose build backend
syft docker:ai-dev-tools-zoomcampskill-project-backend -o cyclonedx-json > security/sbom/backend-image-sbom.cdx.json
```

## Grype Scan

```bash
# Install grype
brew install grype  # macOS

# Scan the SBOM for vulnerabilities
grype sbom:security/sbom/backend-sbom.cdx.json > security/grype/backend-vulns.txt
```

## Notes

- SBOM is conditional on time budget per brief §5. Semgrep alone satisfies the rubric minimum.
- Frontend SBOM can be generated via `syft dir:frontend/` (node_modules may take longer).
- Grype is not currently installed in CI. Results are for reference.
