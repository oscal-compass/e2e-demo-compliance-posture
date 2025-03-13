
.ONESHELL:
SHELL := /bin/bash

SOURCE_INIT = /tmp/venv.e2e-demo
SOURCE = $(SOURCE_INIT)

RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[1;34m
NC := \033[0m # No Color

all: vagrant c2p compliance-posture

compliance-posture:
	@printf "$(BLUE)=> use OSCAL Compass trestle to calucalte NIST 800-53 compliance posture for VM$(NC)\n"
	python python/compliance_posture.py --markdown README.md --observations assessment-results/ubuntu2404/results.json --software component-definitions/Ubuntu_Linux_24.04_LTS/component-definition.json --validation component-definitions/oscap/component-definition.json
	@printf "$(BLUE)=> display compliance posture in default browser$(NC)\n"
	python python/markdown_display.py
	
rule-compare:
	python python/rule_compare.py

c2p: c2p-config c2p-cmd

.SILENT: c2p-cmd
c2p-cmd: venv
	@printf "$(BLUE)=> use OSCAL Compass C2P to deploy tailored profile to VM and get oscap results from VM$(NC)\n"
	source $(SOURCE); \
	python python/compliance_to_policy.py --config python/c2p_plugin/config.yaml --component_definition component-definitions/oscap/component-definition.json --out assessment-results/ubuntu2404/results.json
	@printf "$(BLUE)=> use OSCAL Compass trestle to transform oscap results to OSCAL json$(NC)\n"

.SILENT: c2p-config
c2p-config:
	@printf "$(BLUE)=> create c2p config file$(NC)\n"
	vagrant ssh-config > /tmp/vagrant.ssh.config
	python python/compliance_to_policy_config.py --input /tmp/vagrant.ssh.config --output python/c2p_plugin/config.yaml
	
vagrant: vagrant-halt vagrant-up

.SILENT: vagrant-halt
vagrant-halt:
	@printf "$(BLUE)=> stop VM (if running)$(NC)\n"
	vagrant halt

.SILENT: vagrant-up
vagrant-up:
	@printf "$(BLUE)=> get VM image$(NC)\n"
	rm -fr .vagrant
	cp -p resources/vagrant/ubuntu-24.04/Vagrantfile .
	@printf "$(BLUE)=> start VM$(NC)\n"
	vagrant up
	
# -----

.SILENT: clean
clean: clean-venv

.SILENT: clean-venv
clean-venv:
	rm -fr $(SOURCE)

.SILENT: venv
venv:
	if [ ! -d $(SOURCE) ]; then \
		@printf "$(BLUE)=> create python virtual environment$(NC)\n"; \
		python -m venv $(SOURCE); \
		source $(SOURCE)/bin/activate; \
		@printf "$(BLUE)=> install prereqs$(NC)\n"; \
		pip install -r python/requirements.txt;
	fi
