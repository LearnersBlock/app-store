# To upgrade to new branch, change {strings: url} in database file and the 
# branch ARG in this Dockerfile
FROM php:7.4-fpm-alpine3.14

ARG MOODLE_BRANCH=MOODLE_311_STABLE

RUN apk add --no-cache \
    git \
    nginx \
    supervisor 
    
ADD https://github.com/mlocati/docker-php-extension-installer/releases/latest/download/install-php-extensions /usr/local/bin/
RUN chmod +x /usr/local/bin/install-php-extensions

RUN install-php-extensions \
    gd \
    intl \
    mysqli \
    opcache \
    soap \
    xmlrpc \
    zip

RUN git clone git://git.moodle.org/moodle.git -b $MOODLE_BRANCH --depth 1 --single-branch /var/www/html/moodle

RUN mkdir -p /app/moodledata && \
    chown -R root /app/moodledata && \
    chmod -R 0777 /app/moodledata && \
    chown -R root /var/www/html/moodle && \
    chmod -R 0755 /var/www/html/moodle

RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

COPY moodle-config/config.php /var/www/html/moodle/config.php
COPY nginx-config/nginx.conf /etc/nginx/nginx.conf
COPY php-config/php.ini "$PHP_INI_DIR/conf.d/custom.ini"
COPY php-config/z-php.conf /usr/local/etc/php-fpm.d/z-php.conf
COPY system-config/cron /etc/crontabs/root
COPY system-config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
