# Smart Bank Chatbot
A conversational AI assistant tailored for smart banking operations built during a weekend Hackathon.

## Getting Started

Follow these steps to set up and run the application:

### Prerequisites

Ensure you have the following installed:
- Python 3.8 or higher
- `pip` (Python package manager)
- [Node.js 18.18](https://nodejs.org/en) or later. Consider using `nvm` to switch between `Node.js` versions easily.
- **Docker** (For building and deploying the backend API)
- **Google Cloud SDK** (For deploying to Google Cloud)

Also, ensure you have access to your Google Cloud project.

### API Keys 🔑 
Get your Gemini API key from: [Google AI Studio](https://aistudio.google.com/app/apikey)  
Get your Tavily API key from: [Tavily dashboard](https://app.tavily.com/home)

### Environment Variables
API keys and URLs are stored as environment variables both due to their personal nature and differences in development/production environments.
For example, development/production URLs may differ, so hard-coding them is not a good idea:
```
# .env.development
NEXT_PUBLIC_API_URL=http://localhost:8000

# .env.production
NEXT_PUBLIC_API_URL=https://backend-api-xyz.a.run.app
```
Thus, in your development environment (on your local machine), create a `/backend/.env` file to store environment variables.
Inside, define the following:
```
GEMINI_API_KEY=<YOUR API KEY>
TAVILY_API_KEY=<YOUR API KEY>
```
For now, they only have API keys, but will likely include URL addresses later as well.
(Potentially, use a --env-vars-file flag later on [Google Cloud - Use environment variables](https://cloud.google.com/workflows/docs/use-environment-variables)) 

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/ashleynguci/smart-bank-chatbot.git
    cd smart-bank-chatbot
    ```

2. Install the required dependencies:
    ```bash
    pip install -r backend/requirements.txt
    ```

---

## Local Development Environment
To run Docker Images locally and make sure they work together and communicate as intended, we are using Docker Compose.
Docker Compose is included by default in Docker Desktop - you don't need to install it separately.
It lets us wire services together without needing to manually set up networks, ports, or dependencies.
However, for Google Cloud Run, Docker Compose will not work. 
So if you are ready to deploy, follow the **Build and Deploy Backend API and Frontend** instructions instead.

First, launch Docker and ensure that the Docker Engine is running. Then, to start the local dev environment, run:
    ```
    docker-compose up --build
    ```

The first you run this command, it may take a few minutes to set everything up and running. Subsequent `docker-compose` runs will be much quicker!

Now, the containers are all set up and ready to communicate with one another!
The Frontend UI is accessible at: `http://localhost:3000/`.

To stop the containers and clean up, run:
    ```
    docker-compose down
    ```

### Run Frontend Server
For UI development purposes, it is much more handy to use a dev server instead of a container.
Code changes will be reflected in real time in the browser whenever you save files, speeding up development!

To start a hot-reloading dev server on http://localhost:3000, use the following commands:

1. Navigate to the `frontend` folder.
    ```bash
    cd frontend
    ```

2. Install dependencies
    ```bash
    npm install
    ```

3. Launch the development server.
    ```bash
    npm run dev
    ```

To shut down the server, use `Ctrl + C`.

---

## Build and Deploy Backend API and Frontend

This section will guide you on how to build and deploy the Docker containers to **Google Cloud Run**.

### Set a Backend API URL Environment Variable
We want to instruct the deployed Frontend to call a deployed Backend Cloud API instead of `http://localhost:8000`.
Here, it is assumed that containers have been previously deployed and a link of format `https://<project-link>.a.run.app`
is reserved for the backend container. If not, deploy the Backend first individually.
Subsequent deployments do not change the link, so you can immediately provide it to the frontend container:

1. Create a `/frontend/.env.production` file. Do not push this to Git (.gitignore takes care of this)

2. Inside, paste the link to the deployed Backend API container:
    ```bash
    NEXT_PUBLIC_API_URL=https://<project-link>.a.run.app
    ```

3. The Frontend Docker Image builder below will use this link instead of `http://localhost:8000` in `.env.development`. 

### Build Docker Images

Replace `<your-project-id>` with your Google Cloud project ID.

1. **Navigate to the root directory**:
    ```bash
    cd smart-bank-chatbot
    ```

2. **Build the Backend Docker image** using the following command:
    ```bash
    docker build -t gcr.io/<your-project-id>/nordea-backend ./backend
    ```

3. **Build the Frontend Docker image** using the following command:
    ```bash
    docker build -f Dockerfile.prod -t gcr.io/<your-project-id>/nordea-frontend ./frontend
    ```

### Push the Docker Image to Google Cloud

1. **Authenticate your Google Cloud account** (if not done already):
    ```bash
    gcloud auth login
    ```

2. **Set your Google Cloud project**:
    ```bash
    gcloud config set project <your-project-id>
    ```

3. **Push the Docker image to Google Container Registry**:
    ```bash
    docker push gcr.io/<your-project-id>/nordea-backend
    ```

---

### Deploy the Backend API to Google Cloud Run

1. **Deploy the Docker image to Google Cloud Run**:
    ```bash
    gcloud run deploy nordea-backend \
    --image gcr.io/<your-project-id>/nordea-backend \
    --platform managed \
    --region europe-north1 \
    --allow-unauthenticated \
    --set-env-vars GEMINI_API_KEY=
    ```

`--env-vars-file .env.production.yml` may be used to replace `--set-env-vars` later on.

### Test the Deployed Backend API

Once the backend API is deployed, you can test the `/chat` API endpoint by sending a **POST** request to it. You can use **Postman** or **curl** for testing.

Example using `curl`:
```bash
curl -X 'POST' \
  'https://<your-service-name>.run.app/chat' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "Hello, do I have any unpaid invoices?"
}'
```