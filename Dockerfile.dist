FROM python:3.7

# Install Apache2 web server and environment
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
		apache2 apache2-dev apache2-utils \
		vim locales \
		graphviz
RUN rm -rf /var/lib/apt/lists/*

# Set www-data uid to host given uid, or default uid
ARG WWW_UID=1000
RUN usermod -u $WWW_UID -g 0 www-data

# Copy app files
WORKDIR /opt/opus
COPY favicon* ./
COPY requirements.txt ./
COPY .git ./.git
COPY .htaccess ./.htaccess
COPY uws_client ./uws_client
COPY uws_server ./uws_server
COPY uws_client/wsgi.py ./wsgi_client.py
COPY uws_server/wsgi.py ./wsgi_server.py
COPY test_server.py ./
COPY settings_docker.py ./settings_local.py
COPY apache_opus.conf /etc/apache2/sites-enabled/apache_opus.conf

# Install requirements
RUN pip install -r requirements.txt
# Fix prov issue (missing label attribute in bundle...)
RUN sed -i 's/bundle.label ==/bundle.identifier !=/g' /usr/local/lib/python3.7/site-packages/prov/dot.py
RUN sed -i 's/six.text_type(bundle.label)/six.text_type(bundle.identifier)/g' /usr/local/lib/python3.7/site-packages/prov/dot.py

# Install WSGI and Apache conf
RUN pip install mod-wsgi
RUN rm /etc/apache2/sites-enabled/000-default.conf
RUN mod_wsgi-express module-config > /etc/apache2/mods-enabled/wsgi.conf
# RUN mkdir -p /etc/apache2/ssl
# COPY $WWW_SSL/*.pem /etc/apache2/ssl/

# Run web server
EXPOSE 80
EXPOSE 443
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
