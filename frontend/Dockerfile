# Client-side rendering with Next.js

FROM node:20-alpine AS builder
WORKDIR /app
COPY ./ ./
RUN npm install 

# Build the static site
RUN npm run build

# Stage 2: Serve with a lightweight HTTP server
FROM node:20-alpine
WORKDIR /app

# Install serve
RUN npm install -g serve

# Copy build artifacts
COPY --from=builder /app/out ./out

EXPOSE 3000
CMD ["serve", "-s", "out", "-l", "3000"]