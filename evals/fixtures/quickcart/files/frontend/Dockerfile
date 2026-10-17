FROM node:18 AS build
WORKDIR /app
COPY . .
RUN npm install && npm run build

FROM nginx:1.23
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app /app
