FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Same-origin deploy: nginx proxies /api to the backend, so the frontend
# talks to itself and never needs a real API_URL.
RUN VITE_API_URL= npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
