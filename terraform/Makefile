# Thin wrappers so every stack is driven the same way.
# Prefer `mise run tf:*` from the repo root (see mise.toml). Direct make still works:
#
#   make init ENV=prod          terraform init with the env's backend.hcl
#   make plan ENV=prod          plan into a local .tfplan
#   make apply ENV=prod         apply the saved plan
#   make check                  fmt -check + validate every stack and module
#   make bootstrap-apply        one-time account foundation (local state)
#
# ENV defaults to prod. Terraform and tflint come from mise (terraform >= 1.10).
# AWS credentials go in the environment or ~/.aws (never in the repo).

ENV        ?= prod
ENV_DIR    := envs/$(ENV)
TF         := terraform -chdir=$(ENV_DIR)
STACKS     := bootstrap $(wildcard envs/*)
MODULES    := $(wildcard modules/*)

.PHONY: help init plan apply destroy output fmt fmt-check validate check lint bootstrap-init bootstrap-plan bootstrap-apply

help:
	@sed -n '2,12p' $(MAKEFILE_LIST)

init:
	$(TF) init -input=false -backend-config=backend.hcl

plan: init
	$(TF) plan -input=false -out=tfplan $(ARGS)

apply:
	$(TF) apply -input=false tfplan

destroy: init
	$(TF) destroy $(ARGS)

output:
	$(TF) output $(ARGS)

fmt:
	terraform fmt -recursive

fmt-check:
	terraform fmt -recursive -check -diff

validate:
	@for d in $(STACKS) $(MODULES); do \
		echo "== $$d"; \
		terraform -chdir=$$d init -backend=false -input=false >/dev/null && \
		terraform -chdir=$$d validate || exit 1; \
	done

lint:
	tflint --init --config "$(CURDIR)/.tflint.hcl" >/dev/null
	tflint --recursive --config "$(CURDIR)/.tflint.hcl"

check: fmt-check validate

bootstrap-init:
	terraform -chdir=bootstrap init -input=false

bootstrap-plan: bootstrap-init
	terraform -chdir=bootstrap plan -input=false $(ARGS)

bootstrap-apply: bootstrap-init
	terraform -chdir=bootstrap apply $(ARGS)
