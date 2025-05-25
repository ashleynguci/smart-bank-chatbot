# Smart Bank Chatbot
A conversational AI assistant tailored for smart banking operations built during a weekend Hackathon.

## Getting Started
Follow these steps to set up and run the application:

### Prerequisites
Ensure you have the following installed:
- Python 3.8 to 3.13
- `pip` (Python package manager)
- [Node.js 18.18](https://nodejs.org/en) or later. Consider using `nvm` to switch between `Node.js` versions easily.
- **Docker** (For building and deploying container images)
- **Google Cloud SDK** (For deploying to Google Cloud - you don't need to install this to get the project running if you're not planning on deploying)

Also, if you're deploying, ensure you have access to your Google Cloud project.

### API Keys 🔑 
Get your Gemini API key from: [Google AI Studio](https://aistudio.google.com/app/apikey)  
Get your Tavily API key from: [Tavily dashboard](https://app.tavily.com/home) (Currently not used yet, so not required)

### Environment Variables
API keys and URLs are stored as private environment variables both due to their personal nature and differences in development/production environments.
For example, development/production URLs may differ, so hard-coding them is not a good idea.
Thus, in your development environment (on your local machine), create a `/backend/.env` file to store API key environment variables.
Inside, define the following:
```
GEMINI_API_KEY=<YOUR API KEY>
TAVILY_API_KEY=<YOUR API KEY>
```
For now, they only have API keys, but will likely include an approved frontend URL address later as well.
(Potentially, we may use a --env-vars-file flag later on [Google Cloud - Use environment variables](https://cloud.google.com/workflows/docs/use-environment-variables)) 

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

First, launch Docker and ensure that the Docker Engine is running. Then, to start the local dev environment, at the root of the project run:
    ```
    docker compose up --build
    ```
or
    ```
    docker compose -f 'docker-compose.yml' up -d --build
    ```
    The first time you run this command, it may take a few minutes to set everything up and running. Subsequent `docker compose` runs will be much quicker!
Note that it might take around 30 seconds until backend starts up, as it needs to parse documents first before accepting requests.
The Backend container will not be usable until a 'Application startup complete' message has been shown in the terminal console.

Now, the containers are all set up and ready to communicate with one another!
The Frontend UI is now accessible at: `http://localhost:3000/`.

To stop the containers use `Ctrl + C`, and to clean up, run:
    ```
    docker compose down
    ```

### Run Frontend Server
For UI development purposes, it is much more handy to use a dev server instead of a container.
Code changes will be reflected in real time in the browser whenever you save files, speeding up development!
The Frontend container calls the cloud-hosted Backend API to remove the need to constantly rebuild the Backend.
To ensure that requests are routed correctly:

1. Add a `/frontend/.env.development.local` file

2. Inside, paste the link to the deployed Backend API container:
    ```bash
    NEXT_PUBLIC_API_URL=https://<project-link>.a.run.app
    ```

To start a hot-reloading dev server on `http://localhost:3000`, use the following commands:

3. Navigate to the `frontend` folder.
    ```bash
    cd frontend
    ```

4. Install dependencies
    ```bash
    npm install
    ```

5. Launch the development server.
    ```bash
    npm run dev
    ```

To shut down the server, use `Ctrl + C`.

---

## Build and Deploy Backend API

This section will guide you on how to build and deploy the Backend API Docker container to **Google Cloud Run**.
We will first deploy the Backend, and once this is done, we will continue with the Frontend container (see **Build and Deploy Frontend**)

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

## Build and Deploy Frontend

### Set a Backend API URL Environment Variable
We want to instruct the deployed Frontend to call a deployed Backend Cloud API instead of `http://localhost:8000`.
Now the Backend is deployed and hosted on a reserved link of format `https://<project-link>.a.run.app`. 
Subsequent deployments should not change the link.
Now you can provide the Backend link to the frontend container:

1. Create a `/frontend/.env.production` file. Do not push this to Git (.gitignore takes care of this)

2. Inside, paste the link to the deployed Backend API container:
    ```bash
    NEXT_PUBLIC_API_URL=https://<project-link>.a.run.app
    ```

3. **Build the Frontend Docker image** using the following command:
    ```bash
    docker build -f frontend/Dockerfile.prod -t gcr.io/<your-project-id>/nordea-frontend ./frontend
    ```

4. **Push the Docker image to Google Container Registry**:
    ```bash
    docker push gcr.io/<your-project-id>/nordea-frontend
    ```

5. **Deploy the Docker image to Google Cloud Run**:
    ```bash
    gcloud run deploy nordea-frontend \
    --image gcr.io/<your-project-id>/nordea-frontend \
    --platform managed \
    --region europe-north1 \
    --allow-unauthenticated \
    --port 3000
    ```

Note: `--port 3000` is a temporary fix (even though it works). Cloud Run is trying to verify that the container is listening on port 8080 (its default), so this should be reconfigured elsewhere.