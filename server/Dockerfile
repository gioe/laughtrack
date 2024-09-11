# Start your image with a node base image
FROM node:20-alpine

# The /app directory should act as the main application directory
WORKDIR /app

COPY package.json package.json
COPY package-lock.json package-lock.json

RUN npm install

# Copy local directories to the current local directory of our docker image (/app)
COPY . .

CMD [ "npm", "run", "scrape" ]
