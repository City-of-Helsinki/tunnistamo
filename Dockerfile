# =========================================================
FROM helsinkitest/python-node:3.6-10-slim as staticbuilder
# ---------------------------------------------------------
# Stage for building static files for
# the project. Installs Node as that
# is required for compiling SCSS files.
# =========================================================

RUN apt-install.sh \
      libxmlsec1-dev \
      libxml2-dev \
      pkg-config \
      git \
      curl \
      libpq-dev \
      build-essential

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY package.json /app/package.json
RUN pip install -U pip \
    && pip install --no-cache-dir  -r /app/requirements.txt
RUN npm install

COPY . /app/
RUN python manage.py compilescss \
    && python manage.py collectstatic --noinput

#WORKDIR /app

COPY --chown=1000:1000 requirements.txt /app/requirements.txt
COPY --chown=1000:1000 requirements-prod.txt /app/requirements-prod.txt

# Install main project dependencies and clean up
# Note that production dependencies are installed here as well since
# that is the default state of the image and development stages are
# just extras.
RUN apt-install.sh \
      build-essential \
      libpq-dev \
      gettext \
      git \
      libxmlsec1-dev \
      libxml2-dev \
      netcat \
      pkg-config \
    && pip install -U pip \
    && pip install --no-cache-dir  -r /app/requirements.txt \
    && pip install --no-cache-dir  -r /app/requirements-prod.txt \
    && apt-cleanup.sh build-essential pkg-config git

COPY docker-entrypoint.sh /app


# STore static files under /var to not conflict with development volume mount
ENV STATIC_ROOT /var/tunnistamo/static
ENV NODE_MODULES_ROOT /var/tunnistamo/node_modules
RUN cp -r /app/static /var/tunnistamo/
RUN cp -r /app/node_modules /var/tunnistamo/node_modules


#WORKDIR /app
COPY --chown=1000:1000 requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir  -r /app/requirements-dev.txt \
  && pip install --no-cache-dir pip-tools

ENV DEV_SERVER=1

COPY --chown=1000:1000 . /app/

USER 1000
EXPOSE 8000/tcp
ENTRYPOINT ["./docker-entrypoint.sh"]

# ===========================================
# FROM helsinkitest/python:3.6-slim as appbase
# ===========================================



# =========================
# FROM appbase as development
# =========================

# ==========================
# FROM appbase as production
# ==========================

# COPY --chown=1000:1000 . /app/

# USER 1000
# EXPOSE 8000/tcp
