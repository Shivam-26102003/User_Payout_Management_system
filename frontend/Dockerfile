FROM node:22-alpine

WORKDIR /workspace

# Copy dependencies list
COPY package.json .

# Install dependencies
RUN npm install

# Copy all source files
COPY . .

EXPOSE 3000

# Start Next.js in hot-reloading development mode
CMD ["npm", "run", "dev"]
