# =========================================================
FROM helsinkitest/python-node:3.9-14-slim as staticbuilder
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
COPY package-lock.json /app/package-lock.json
RUN pip install -U pip \
    && pip install --no-cache-dir  -r /app/requirements.txt
RUN npm install

COPY . /app/
RUN python manage.py compilescss \
    && python manage.py collectstatic --noinput

# ===========================================
FROM helsinkitest/python:3.9-slim as appbase
# ===========================================

WORKDIR /app

COPY --chown=appuser:appuser requirements.txt /app/requirements.txt
COPY --chown=appuser:appuser requirements-prod.txt /app/requirements-prod.txt

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
ENTRYPOINT ["./docker-entrypoint.sh"]

# STore static files under /var to not conflict with development volume mount
ENV STATIC_ROOT /var/tunnistamo/static
ENV MEDIA_ROOT /var/tunnistamo/media
ENV NODE_MODULES_ROOT /var/tunnistamo/node_modules
ENV APP_URL_PATH /
COPY --from=staticbuilder --chown=appuser:appuser /app/static /var/tunnistamo/static
COPY --from=staticbuilder --chown=appuser:appuser /app/node_modules /var/tunnistamo/node_modules

COPY --chown=appuser:appuser . /app/

USER appuser
RUN python manage.py compilemessages

# =========================
FROM appbase as development
# =========================

COPY --chown=appuser:appuser requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

ENV DEV_SERVER=1

USER appuser
EXPOSE 8000/tcp

# ==========================
FROM appbase as production
# ==========================

USER appuser
EXPOSE 8000/tcp
