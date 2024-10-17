VENV := .venv
VENV_SENTINEL := $(VENV)/.sentinel
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip


.PHONY: ensure_out_of_venv
ensure_out_of_venv:
ifdef VIRTUAL_ENV
	$(error "Please deactivate your virtual environment")
endif

.PHONY: $(VENV)
$(VENV):
	$(MAKE) $(VENV_SENTINEL)

.PHONY: clean_venv
clean_venv: ensure_out_of_venv
	rm -rf $(VENV)
	python3 -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip wheel

$(VENV_SENTINEL): requirements.txt
	$(MAKE) clean_venv
	$(VENV_PIP) install -r $^
	touch $(VENV_SENTINEL)

.PHONY: update_requirements
update_requirements: requirements-loose.txt
	$(MAKE) clean_venv
	$(VENV_PIP) install -r $^
	$(VENV_PIP) freeze > requirements.txt
	$(MAKE) $(VENV)

.PHONY: install
install: $(VENV)
	ln -s $(PWD) $(HOME)/sync_gh_keys
	mkdir -p $(HOME)/.config/systemd/user/
	install sync-gh-keys.service sync-gh-keys.timer $(HOME)/.config/systemd/user/
	systemctl --user enable sync-gh-keys.timer
	echo "Make sure to add SYNC_GH_USERS to ~/.config/environment.d/sync_gh_users.conf !"
