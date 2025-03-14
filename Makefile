
.ONESHELL:
SHELL := /bin/bash

SOURCE_INIT = /tmp/venv.e2e-demo
SOURCE = $(SOURCE_INIT)/bin/activate

RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[1;34m
NC := \033[0m # No Color

# -----

all:
	@printf "$(BLUE)=> use command 'make demo' or 'make clean-up'$(NC)\n"
	
demo: init compliance-posture display-posture
clean-up: vagrant-stop

init: vagrant-start c2p 

# -----

compliance-posture:
	@printf "$(BLUE)=> use OSCAL Compass trestle to calucalte NIST 800-53 compliance posture for VM$(NC)\n"
	python python/compliance_posture.py --markdown README.md --observations assessment-results/ubuntu2404/results.json --software component-definitions/Ubuntu_Linux_24.04_LTS/component-definition.json --validation component-definitions/oscap/component-definition.json

display-posture:
	@printf "$(BLUE)=> display compliance posture in default browser$(NC)\n"
	python python/markdown_display.py

# -----

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

# -----

vagrant-start: vagrant-init vagrant-up
vagrant-stop: vagrant-halt

.SILENT: vagrant-init
vagrant-init:
	@printf "$(BLUE)=> get VM image$(NC)\n"
	cp -p resources/vagrant/ubuntu-24.04/Vagrantfile .

.SILENT: vagrant-up
vagrant-up:
	@printf "$(BLUE)=> start VM (if not already running)$(NC)\n"
	vagrant up

.SILENT: vagrant-halt
vagrant-halt:
	@printf "$(BLUE)=> stop VM$(NC)\n"
	vagrant halt
	rm -fr .vagrant
	
# -----

.SILENT: clean-venv
clean-venv:
	rm -fr $(SOURCE)

.SILENT: venv
venv:
	if [ ! -d $(SOURCE_INIT) ]; then \
		@printf "$(BLUE)=> create python virtual environment$(NC)\n"; \
		python -m venv $(SOURCE_INIT); \
		source $(SOURCE); \
		@printf "$(BLUE)=> install prereqs$(NC)\n"; \
		pip install -r python/requirements.txt;
	fi
