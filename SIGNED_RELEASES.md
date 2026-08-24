# Signed assessment releases

The `main` release workflow verifies a configured SSP release before publishing a signed assessment-results package. The package contains the current assessment results, the component definitions consumed by the compliance-posture calculation, and the complete verified SSP package.

The assessment package signature covers the canonical SHA-256 digests of the assessment inputs and the upstream SSP manifest. The nested SSP signature separately proves the integrity and approval of the SSP artifacts. Consumers must verify both layers.

The current assessment output is a JSON results collection rather than a complete top-level OSCAL Assessment Results document, so the workflow creates its package manifest explicitly instead of using `trestle generate-manifest`.

## Repository configuration

Set the `SSP_RELEASE_TAG` repository variable to the SSP release consumed by this workflow, for example `v0.3.0`.

Configure these GitHub Actions secrets:

- `SSP_SIGNING_PUBLIC_KEY`: the independently trusted public key for SSP package verification;
- `ASSESSMENT_SIGNING_PRIVATE_KEY`: the encrypted PEM private key used to sign the assessment package;
- `ASSESSMENT_SIGNING_KEY_PASSWORD`: the private-key password;
- `ASSESSMENT_SIGNING_PUBLIC_KEY`: the public key used to verify the assessment package before publication.

Generate an encrypted Ed25519 assessment key pair locally:

```bash
export ASSESSMENT_SIGNING_KEY_PASSWORD='replace-with-a-strong-password'
openssl genpkey -algorithm ed25519 -aes-256-cbc \
  -pass env:ASSESSMENT_SIGNING_KEY_PASSWORD \
  -out assessment-private.pem
openssl pkey -in assessment-private.pem \
  -passin env:ASSESSMENT_SIGNING_KEY_PASSWORD \
  -pubout -out assessment-public.pem
chmod 600 assessment-private.pem
```

Store the private key, password, and public key as the corresponding `ASSESSMENT_SIGNING_*` secrets. Obtain `SSP_SIGNING_PUBLIC_KEY` independently from the maintainers of the SSP release; do not take a replacement key from the release being verified.

## Verification

Download and extract `assessment-results-package-<tag>.tar.gz`, then verify the assessment package with an independently trusted assessment public key:

```bash
trestle verify-manifest \
  --beta \
  --manifest assessment-signing-manifest.json \
  --signature assessment-signing-manifest.dsse \
  --public-key trusted-assessment-public.pem
```

Verify the nested SSP package with its independently trusted public key:

```bash
trestle verify-manifest \
  --beta \
  --manifest upstream/ssp/ssp-signing-manifest.json \
  --signature upstream/ssp/ssp-signing-manifest.dsse \
  --public-key trusted-ssp-public.pem
```
