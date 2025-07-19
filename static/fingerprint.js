// static/fingerprint.js

async function getFingerprint() {
  const msg = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(navigator.userAgent + navigator.language + screen.width + screen.height + screen.colorDepth)
  );
  return Array.from(new Uint8Array(msg))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}
