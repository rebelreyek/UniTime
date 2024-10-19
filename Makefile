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

.PHONY: build
build:
	docker build -t student-app .

.PHONY: deploy
deploy:
	# TODO: Install awscli, lightsailctl in venv
	aws lightsail push-container-image  --service-name student-app --label student-app --image student-app:latest

.PHONY: run
run: $(VENV)
	$(VENV_PYTHON) -m flask --app student-app/app.py run

.PHONY: debug
debug: $(VENV)
	$(VENV_PYTHON) -m flask --app student-app/app.py run --debug
