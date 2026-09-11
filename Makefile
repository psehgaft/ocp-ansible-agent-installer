INVENTORY ?= inventories/sample/hosts.yml
VAULT_ARGS ?= --ask-vault-pass

.PHONY: collections vault preflight validate discover test-media mirror boot install eject day2-render day2-deploy gui-test gui-build gui-run workshop

collections:
	ansible-galaxy collection install -r requirements.yml

vault:
	ansible-playbook playbooks/day0/create-vault.yml

preflight:
	./scripts/preflight.sh $(INVENTORY)

validate:
	./scripts/validate.sh $(INVENTORY)

discover:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/day0/discover-bmc.yml

test-media:
	@test -n "$(HOST)" || (echo "Set HOST=<inventory-host>"; exit 1)
	@test -n "$(TEST_ISO_URL)" || (echo "Set TEST_ISO_URL=<http(s)-url>"; exit 1)
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) --limit $(HOST) -e test_iso_url=$(TEST_ISO_URL) -e bmc_wait_for_node_ssh=false playbooks/03-test-virtual-media.yml

mirror:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/day0/prepare-mirror.yml

boot:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/02-boot-discovery-iso.yml

install:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/day0/install.yml

eject:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/90-eject-media.yml

day2-render:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/day2/render-gitops.yml

day2-deploy:
	ansible-playbook -i $(INVENTORY) $(VAULT_ARGS) playbooks/day2/bootstrap-gitops.yml

gui-test:
	go test -race ./...
	python3 -m pytest -q tests/test_gui_config.py

gui-build:
	podman build -f Containerfile -t ocp-ansible-agent-installer-ui:gui .

gui-run:
	@test -n "$(INSTALLER_UI_ADMIN_TOKEN)" || (echo "Set INSTALLER_UI_ADMIN_TOKEN to a random token of at least 16 characters"; exit 1)
	podman run --rm --name ocp-installer-ui -p 127.0.0.1:8080:8080 \
		-e INSTALLER_UI_AUTH_TOKENS="$(INSTALLER_UI_ADMIN_TOKEN)=admin" \
		-v ocp-installer-ui-data:/data:Z ocp-ansible-agent-installer-ui:gui

workshop:
	@echo "Standalone guide: WORKSHOP.md"
	@echo "Showroom-style source: workshop/documentation/modules/ROOT/pages"
