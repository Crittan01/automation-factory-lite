FROM node:20-alpine

WORKDIR /workspace/apps/frontend

COPY apps/frontend/package.json ./
RUN npm install

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]
