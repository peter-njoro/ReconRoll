FROM nginx:alpine

# Remove default config and bake in ours
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# SSL certs — mount via ECS secrets or bake in for internal use
# COPY certs/selfsigned.crt /etc/nginx/certs/selfsigned.crt
# COPY certs/selfsigned.key /etc/nginx/certs/selfsigned.key

EXPOSE 80 443
