#!/usr/bin/env bash

set -euo pipefail

required_variables=(
    VERSION_TAG
    GH_TOKEN
    GITHUB_REPOSITORY
    SSP_RELEASE_TAG
    SSP_SIGNING_PUBLIC_KEY
    ASSESSMENT_SIGNING_PRIVATE_KEY
    ASSESSMENT_SIGNING_KEY_PASSWORD
    ASSESSMENT_SIGNING_PUBLIC_KEY
)

for variable in "${required_variables[@]}"; do
    if [[ -z "${!variable:-}" ]]; then
        echo "Required environment variable is not set: ${variable}" >&2
        exit 1
    fi
done

if [[ ! "${VERSION_TAG}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
    [[ ! "${SSP_RELEASE_TAG}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo 'Release tags contain unsupported characters.' >&2
    exit 1
fi

ssp_repository="${SSP_RELEASE_REPOSITORY:-oscal-compass/e2e-demo-ssp}"
release_tag="v${VERSION_TAG#v}"
work_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/assessment-signing.XXXXXX")
package_root="${work_dir}/package"
ssp_root="${package_root}/upstream/ssp"
ssp_extract_root="${work_dir}/ssp-extracted"
assessment_manifest="${package_root}/assessment-signing-manifest.json"
assessment_envelope="${package_root}/assessment-signing-manifest.dsse"
assessment_archive="${work_dir}/assessment-results-package-${release_tag}.tar.gz"

cleanup() {
    rm -rf "${work_dir}"
}
trap cleanup EXIT

umask 077
mkdir -p "${ssp_root}" "${ssp_extract_root}"
printf '%s\n' "${SSP_SIGNING_PUBLIC_KEY}" > "${work_dir}/ssp-public.pem"
printf '%s\n' "${ASSESSMENT_SIGNING_PRIVATE_KEY}" > "${work_dir}/assessment-private.pem"
printf '%s\n' "${ASSESSMENT_SIGNING_PUBLIC_KEY}" > "${work_dir}/assessment-public.pem"

ssp_archive="${work_dir}/ssp-package-${SSP_RELEASE_TAG}.tar.gz"
gh release download "${SSP_RELEASE_TAG}" \
    --repo "${ssp_repository}" \
    --pattern "$(basename "${ssp_archive}")" \
    --dir "${work_dir}"

python3 - "${ssp_archive}" "${ssp_extract_root}" <<'PY'
import pathlib
import sys
import tarfile

archive = pathlib.Path(sys.argv[1])
destination = pathlib.Path(sys.argv[2])
with tarfile.open(archive, 'r:gz') as package:
    package.extractall(destination, filter='data')
PY

python3 - "${ssp_extract_root}" "${ssp_root}" <<'PY'
import json
import pathlib
import shutil
import sys

source_root = pathlib.Path(sys.argv[1]).resolve()
destination_root = pathlib.Path(sys.argv[2]).resolve()
manifest_name = 'ssp-signing-manifest.json'
envelope_name = 'ssp-signing-manifest.dsse'

with (source_root / manifest_name).open(encoding='utf-8') as manifest_file:
    manifest = json.load(manifest_file)

artifact_paths = [pathlib.PurePosixPath(artifact['uri']) for artifact in manifest['artifacts']]
artifact_paths.extend((pathlib.PurePosixPath(manifest_name), pathlib.PurePosixPath(envelope_name)))

for artifact_path in artifact_paths:
    if artifact_path.is_absolute() or '..' in artifact_path.parts:
        raise ValueError(f'Unsafe SSP package artifact path: {artifact_path}')
    source = (source_root / pathlib.Path(*artifact_path.parts)).resolve()
    if not source.is_relative_to(source_root) or not source.is_file():
        raise ValueError(f'Invalid SSP package artifact: {artifact_path}')
    destination = destination_root / pathlib.Path(*artifact_path.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
PY

trestle verify-manifest \
    --beta \
    --manifest "${ssp_root}/ssp-signing-manifest.json" \
    --signature "${ssp_root}/ssp-signing-manifest.dsse" \
    --public-key "${work_dir}/ssp-public.pem"

copy_artifact() {
    local source=$1
    local destination="${package_root}/${source}"
    test -f "${source}"
    mkdir -p "$(dirname "${destination}")"
    cp "${source}" "${destination}"
}

assessment_results="assessment-results/ubuntu2404/results.json"
software_definition="component-definitions/Ubuntu_Linux_24.04_LTS/component-definition.json"
validation_definition="component-definitions/oscap/component-definition.json"
ssp_manifest="upstream/ssp/ssp-signing-manifest.json"

copy_artifact "${assessment_results}"
copy_artifact "${software_definition}"
copy_artifact "${validation_definition}"

jq -n \
    --arg assessment_results "${assessment_results}" \
    --arg software_definition "${software_definition}" \
    --arg validation_definition "${validation_definition}" \
    --arg ssp_manifest "${ssp_manifest}" \
    '{
        primaryArtifact: $assessment_results,
        artifacts: [
            {name: $assessment_results, uri: $assessment_results, mediaType: "application/json"},
            {name: $software_definition, uri: $software_definition, mediaType: "application/oscal+json"},
            {name: $validation_definition, uri: $validation_definition, mediaType: "application/oscal+json"},
            {name: $ssp_manifest, uri: $ssp_manifest, mediaType: "application/json"}
        ]
    }' > "${assessment_manifest}"

trestle sign-manifest \
    --beta \
    --manifest "${assessment_manifest}" \
    --private-key "${work_dir}/assessment-private.pem" \
    --key-password-env ASSESSMENT_SIGNING_KEY_PASSWORD \
    -o "${assessment_envelope}"

trestle verify-manifest \
    --beta \
    --manifest "${assessment_manifest}" \
    --signature "${assessment_envelope}" \
    --public-key "${work_dir}/assessment-public.pem"

tar -czf "${assessment_archive}" -C "${package_root}" .
gh release upload "${release_tag}" "${assessment_archive}" --repo "${GITHUB_REPOSITORY}"
