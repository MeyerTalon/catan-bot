#!/usr/bin/env bash
# Create the Cognito user pool, app client, and a dev user in moto for the
# local stack and write the ids to /out (= .generated/ at the repo root). Runs
# in the amazon/aws-cli image (see docker-compose.yml); AWS_ENDPOINT_URL points
# at moto.
#
# The pool and client mirror terraform/modules/auth/main.tf so local auth
# behaves like prod: email is the username, same password policy, same auth
# flows and token lifetimes, no client secret. --read-attributes is explicit
# because moto only puts listed attributes in the id token, while real Cognito
# includes them all when the list is unset. Idempotent: existing resources are
# reused, and moto's HASH id strategy keeps the ids stable across restarts.
set -euo pipefail

POOL_NAME=catan-local
CLIENT_NAME="${POOL_NAME}-backend"
DEV_USER_EMAIL="${DEV_USER_EMAIL:-admin@example.com}"
DEV_USER_PASSWORD="${DEV_USER_PASSWORD:-Admin123}"
OUT_DIR=/out
MOTO_HOST_PORT="${MOTO_HOST_PORT:-5001}"
POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-5432}"

log() {
  printf '==> %s\n' "$*"
}

pool_id="$(aws cognito-idp list-user-pools --max-results 60 \
  --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" --output text)"

if [[ -z "$pool_id" || "$pool_id" == "None" ]]; then
  log "creating user pool ${POOL_NAME}"
  pool_id="$(aws cognito-idp create-user-pool \
    --pool-name "$POOL_NAME" \
    --username-attributes email \
    --auto-verified-attributes email \
    --username-configuration CaseSensitive=false \
    --policies 'PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false,TemporaryPasswordValidityDays=7}' \
    --account-recovery-setting 'RecoveryMechanisms=[{Name=verified_email,Priority=1}]' \
    --schema 'Name=email,AttributeDataType=String,Required=true,Mutable=true,StringAttributeConstraints={MinLength=1,MaxLength=256}' \
    --query UserPool.Id --output text)"
else
  log "user pool ${POOL_NAME} exists (${pool_id})"
fi

client_id="$(aws cognito-idp list-user-pool-clients --user-pool-id "$pool_id" --max-results 60 \
  --query "UserPoolClients[?ClientName=='${CLIENT_NAME}'].ClientId | [0]" --output text)"

if [[ -z "$client_id" || "$client_id" == "None" ]]; then
  log "creating app client ${CLIENT_NAME}"
  client_id="$(aws cognito-idp create-user-pool-client \
    --user-pool-id "$pool_id" \
    --client-name "$CLIENT_NAME" \
    --no-generate-secret \
    --read-attributes email name \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
    --prevent-user-existence-errors ENABLED \
    --enable-token-revocation \
    --access-token-validity 60 \
    --id-token-validity 60 \
    --refresh-token-validity 30 \
    --token-validity-units AccessToken=minutes,IdToken=minutes,RefreshToken=days \
    --query UserPoolClient.ClientId --output text)"
else
  log "app client ${CLIENT_NAME} exists (${client_id})"
fi

# dev user, already confirmed with a permanent password (the password must
# satisfy the pool policy above). moto's rng is re-seeded first so the user's
# sub is the same on every start: the users row the backend creates for it
# then stays valid even when moto alone restarts.
if aws cognito-idp admin-get-user --user-pool-id "$pool_id" --username "$DEV_USER_EMAIL" >/dev/null 2>&1; then
  log "dev user ${DEV_USER_EMAIL} exists"
else
  log "creating dev user ${DEV_USER_EMAIL}"
  curl -fsS -X POST "${AWS_ENDPOINT_URL}/moto-api/seed?a=42" >/dev/null
  aws cognito-idp admin-create-user \
    --user-pool-id "$pool_id" \
    --username "$DEV_USER_EMAIL" \
    --user-attributes Name=email,Value="$DEV_USER_EMAIL" Name=email_verified,Value=true Name=name,Value=admin \
    --message-action SUPPRESS >/dev/null
  aws cognito-idp admin-set-user-password \
    --user-pool-id "$pool_id" \
    --username "$DEV_USER_EMAIL" \
    --password "$DEV_USER_PASSWORD" \
    --permanent
fi

mkdir -p "$OUT_DIR"

# read by the backend container (docker-compose.yml env_file)
cat >"${OUT_DIR}/cognito.env" <<EOF
COGNITO_USER_POOL_ID=${pool_id}
COGNITO_CLIENT_ID=${client_id}
COGNITO_JWKS_URL=http://moto:5000/${pool_id}/.well-known/jwks.json
EOF

# for running the backend on the host against the stack:
#   set -a; . .generated/host.env; set +a; mise run be:dev
cat >"${OUT_DIR}/host.env" <<EOF
DATABASE_URL=postgresql://catan:catan@localhost:${POSTGRES_HOST_PORT}/catan
COGNITO_REGION=us-west-2
COGNITO_USER_POOL_ID=${pool_id}
COGNITO_CLIENT_ID=${client_id}
COGNITO_ENDPOINT_URL=http://localhost:${MOTO_HOST_PORT}
COGNITO_JWKS_URL=http://localhost:${MOTO_HOST_PORT}/${pool_id}/.well-known/jwks.json
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
EOF

# read by the db-seed service, which logs the dev user in once so the backend
# creates its users row through the normal auth path
cat >"${OUT_DIR}/dev-user.json" <<EOF
{"email": "${DEV_USER_EMAIL}", "password": "${DEV_USER_PASSWORD}"}
EOF

log "wrote ${OUT_DIR}/cognito.env, ${OUT_DIR}/host.env, and ${OUT_DIR}/dev-user.json"
log "pool ${pool_id}, client ${client_id}, dev user ${DEV_USER_EMAIL} / ${DEV_USER_PASSWORD}"
