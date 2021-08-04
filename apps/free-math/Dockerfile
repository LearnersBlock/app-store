FROM node:14.17.0 as node-build-step

RUN apt-get update && apt-get install \
    git \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev -y

# Clears Docker cache when new commit is pushed
ADD https://api.github.com/repos/jaltekruse/free-math/git/refs/heads/master version.json

RUN git clone https://github.com/jaltekruse/Free-Math.git

WORKDIR /Free-Math

RUN npm install

RUN npm run build


FROM nginx:alpine

COPY --from=node-build-step /Free-Math/build /usr/share/nginx/html
