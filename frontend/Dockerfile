FROM node:22-alpine

WORKDIR /workspace

# Copy dependency manifests for reproducible installs
COPY package.json package-lock.json ./

# Install exact dependency versions (faster, reproducible)
RUN npm ci

# Copy all source files
COPY . .

EXPOSE 3000

# Bind to all interfaces so the port is reachable outside the container
ENV HOSTNAME=0.0.0.0

# Start Next.js in hot-reloading development mode
CMD ["npm", "run", "dev"]
