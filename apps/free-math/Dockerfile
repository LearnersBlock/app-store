FROM node:14.17.0-alpine3.13 as node-build-step

RUN apk add git

RUN git clone https://github.com/jaltekruse/Free-Math.git

WORKDIR /Free-Math

RUN npm install

RUN npm run build

FROM nginx

COPY --from=node-build-step /Free-Math/build /usr/share/nginx/html
