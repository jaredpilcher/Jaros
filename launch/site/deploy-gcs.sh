#!/usr/bin/env bash
#
# Deploy the Jaros landing page (launch/site/index.html) to a Google Cloud Storage
# bucket served over a global HTTPS load balancer with a Google-managed TLS
# certificate, for a custom domain (default: jarosai.com).
#
# Why a load balancer and not just the bucket? A GCS bucket can serve a custom
# domain directly only over plain HTTP (CNAME to c.storage.googleapis.com). For
# HTTPS on your own domain you put the bucket behind an external HTTPS load
# balancer with a managed cert. That is what this script sets up. (The LB has a
# small standing cost — roughly ~$18/mo for the forwarding rule — plus minimal
# egress/CDN. If you'd rather avoid that, see "Cheaper alternatives" at the bottom.)
#
# ─────────────────────────────────────────────────────────────────────────────
# PREREQUISITES (one time)
#   1. Install the Google Cloud SDK         https://cloud.google.com/sdk/docs/install
#        …or just run this in Cloud Shell (gcloud is preinstalled & authed):
#        https://shell.cloud.google.com  ->  git clone the repo  ->  run this script.
#   2. Authenticate + pick your project:
#        gcloud auth login
#        gcloud config set project YOUR_PROJECT_ID
#
# RUN
#   cd launch/site
#   PROJECT=YOUR_PROJECT_ID DOMAIN=jarosai.com ./deploy-gcs.sh
#
# The script is idempotent: re-running it re-uploads the page and skips resources
# that already exist. At the end it prints the static IP and the exact DNS records
# to add in Squarespace.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
DOMAIN="${DOMAIN:-jarosai.com}"
BUCKET="${BUCKET:-${DOMAIN//./-}-site}"   # e.g. jarosai-com-site (name is arbitrary behind the LB)
LOCATION="${LOCATION:-US}"                 # multi-region for the bucket
PREFIX="${PREFIX:-jaros}"                  # name prefix for the LB resources
SRC="$(cd "$(dirname "$0")" && pwd)/index.html"

[ -n "$PROJECT" ] || { echo "ERROR: set PROJECT=your-project-id (or run: gcloud config set project ...)"; exit 1; }
[ -f "$SRC" ]     || { echo "ERROR: $SRC not found"; exit 1; }

echo "Project : $PROJECT"
echo "Domain  : $DOMAIN  (+ www.$DOMAIN)"
echo "Bucket  : gs://$BUCKET"
echo

gcloud config set project "$PROJECT" >/dev/null
echo "==> enabling APIs (compute, storage)"
gcloud services enable compute.googleapis.com storage.googleapis.com >/dev/null

# helper: run a create command only if the describe fails (idempotent)
ensure() { local desc="$1"; shift; if eval "$desc" >/dev/null 2>&1; then echo "    exists: skip"; else "$@"; fi; }

echo "==> 1/8 bucket + static-website config"
if ! gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET" --location="$LOCATION" --uniform-bucket-level-access
fi
gcloud storage buckets update "gs://$BUCKET" \
  --web-main-page-suffix=index.html --web-error-page=index.html >/dev/null

echo "==> 2/8 upload index.html (short cache so updates show quickly)"
gcloud storage cp --cache-control="public,max-age=300" "$SRC" "gs://$BUCKET/index.html"

echo "==> 3/8 make the object publicly readable"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member=allUsers --role=roles/storage.objectViewer >/dev/null

echo "==> 4/8 reserve a global static IP"
ensure "gcloud compute addresses describe ${PREFIX}-ip --global" \
  gcloud compute addresses create "${PREFIX}-ip" --global
IP="$(gcloud compute addresses describe "${PREFIX}-ip" --global --format='value(address)')"

echo "==> 5/8 backend bucket (Cloud CDN on) + URL map"
ensure "gcloud compute backend-buckets describe ${PREFIX}-backend" \
  gcloud compute backend-buckets create "${PREFIX}-backend" --gcs-bucket-name="$BUCKET" --enable-cdn
ensure "gcloud compute url-maps describe ${PREFIX}-urlmap" \
  gcloud compute url-maps create "${PREFIX}-urlmap" --default-backend-bucket="${PREFIX}-backend"

echo "==> 6/8 Google-managed TLS cert for $DOMAIN + www.$DOMAIN"
ensure "gcloud compute ssl-certificates describe ${PREFIX}-cert --global" \
  gcloud compute ssl-certificates create "${PREFIX}-cert" --global --domains="$DOMAIN,www.$DOMAIN"

echo "==> 7/8 HTTPS proxy + :443 forwarding rule"
ensure "gcloud compute target-https-proxies describe ${PREFIX}-https-proxy" \
  gcloud compute target-https-proxies create "${PREFIX}-https-proxy" \
    --url-map="${PREFIX}-urlmap" --ssl-certificates="${PREFIX}-cert"
ensure "gcloud compute forwarding-rules describe ${PREFIX}-https-fr --global" \
  gcloud compute forwarding-rules create "${PREFIX}-https-fr" --global \
    --target-https-proxy="${PREFIX}-https-proxy" --ports=443 --address="${PREFIX}-ip"

echo "==> 8/8 HTTP->HTTPS redirect on :80"
if ! gcloud compute url-maps describe "${PREFIX}-redirect" >/dev/null 2>&1; then
  gcloud compute url-maps import "${PREFIX}-redirect" --global --quiet --source=- <<'YAML'
name: jaros-redirect
defaultUrlRedirect:
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  httpsRedirect: true
YAML
fi
ensure "gcloud compute target-http-proxies describe ${PREFIX}-http-proxy" \
  gcloud compute target-http-proxies create "${PREFIX}-http-proxy" --url-map="${PREFIX}-redirect"
ensure "gcloud compute forwarding-rules describe ${PREFIX}-http-fr --global" \
  gcloud compute forwarding-rules create "${PREFIX}-http-fr" --global \
    --target-http-proxy="${PREFIX}-http-proxy" --ports=80 --address="${PREFIX}-ip"

cat <<EOF

────────────────────────────────────────────────────────────────────────────
DONE provisioning. Load balancer IP:  $IP

NEXT — set these DNS records in Squarespace
  (Domains -> $DOMAIN -> DNS / DNS Settings -> add a custom record):

    TYPE   HOST   VALUE
    A      @      $IP
    A      www    $IP

  Remove any pre-existing A/CNAME records on @ or www that Squarespace added for
  parking, or they will conflict.

THEN
  • DNS propagates (minutes to a few hours).
  • The managed certificate goes ACTIVE only AFTER the domain resolves to $IP;
    this can take 15–60 min. Check with:
       gcloud compute ssl-certificates describe ${PREFIX}-cert --global \\
         --format='value(managed.status, managed.domainStatus)'
  • Once ACTIVE, https://$DOMAIN and https://www.$DOMAIN serve the page (HTTP
    auto-redirects to HTTPS).

To publish edits later, just re-run:  PROJECT=$PROJECT DOMAIN=$DOMAIN ./deploy-gcs.sh
────────────────────────────────────────────────────────────────────────────

Cheaper alternatives (no standing LB cost), if you want them instead:
  • Firebase Hosting: \`firebase init hosting\` (public dir = launch/site) then
    \`firebase deploy\`; add the custom domain in the Firebase console. Free TLS.
  • Cloudflare in front of the bucket: keep the bucket public, proxy the domain
    through Cloudflare (free) for TLS, point Squarespace NS/records at Cloudflare.
EOF
