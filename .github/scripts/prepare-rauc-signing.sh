#!/usr/bin/env bash
set -euo pipefail

if [[ -z ${RAUC_CERTIFICATE:-} || -z ${RAUC_PRIVATE_KEY:-} ]]; then
    echo '::error::Full image builds require stable RAUC_CERTIFICATE and RAUC_PRIVATE_KEY secrets. Never regenerate the signing key between releases.' >&2
    exit 1
fi

output=${1:?build directory required}
umask 077
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

printf '%b\n' "$RAUC_CERTIFICATE" > "$tmp/cert.pem"
if ! grep -q -- '-----BEGIN CERTIFICATE-----' "$tmp/cert.pem"; then
    printf -- '-----BEGIN CERTIFICATE-----\n%b\n-----END CERTIFICATE-----\n' "$RAUC_CERTIFICATE" > "$tmp/cert.pem"
fi
printf '%b\n' "$RAUC_PRIVATE_KEY" > "$tmp/key.pem"
if ! grep -qE -- '-----BEGIN (RSA |EC )?PRIVATE KEY-----' "$tmp/key.pem"; then
    printf -- '-----BEGIN PRIVATE KEY-----\n%b\n-----END PRIVATE KEY-----\n' "$RAUC_PRIVATE_KEY" > "$tmp/key.pem"
fi

openssl x509 -in "$tmp/cert.pem" -noout -checkend 65664000 || {
    echo '::error::RAUC certificate must be valid for at least 760 more days.' >&2
    exit 1
}
openssl verify -partial_chain -trusted "$tmp/cert.pem" "$tmp/cert.pem"
openssl pkey -in "$tmp/key.pem" -passin pass: -check -noout
openssl x509 -in "$tmp/cert.pem" -pubkey -noout > "$tmp/cert.pub"
openssl pkey -in "$tmp/key.pem" -passin pass: -pubout > "$tmp/key.pub"
if ! cmp -s "$tmp/cert.pub" "$tmp/key.pub"; then
    echo '::error::RAUC certificate and private key do not match.' >&2
    exit 1
fi

install -m 0644 "$tmp/cert.pem" "$output/cert.pem"
install -m 0600 "$tmp/key.pem" "$output/key.pem"
openssl x509 -in "$output/cert.pem" -noout -sha256 -fingerprint -enddate
