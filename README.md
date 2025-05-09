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
Thus, in your development environment (on your local machine), create a `.env` file at the root of the project to store environment variables.
Inside, define the following variables:
```
GEMINI_API_KEY=<YOUR API KEY>
TAVILY_API_KEY=<YOUR API KEY>

```
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

## Docker: Build, Run and Deploy Backend API and Frontend

This section will guide you on how to build and deploy the backend API to **Google Cloud Run** using **Docker**.

### Build Docker Images

Replace `<your-project-id>` with your Google Cloud project ID.

1. **Navigate to the root directory**:
    ```bash
    cd smart-bank-chatbot
    ```

2. **Build the Backend Docker image** using the following command:
    ```bash
    docker build -t gcr.io/<your-project-id>/nordea-backend -f backend/Dockerfile .
    ```

3. **Build the Frontend Docker image** using the following command:
    ```bash
    docker build -t gcr.io/<your-project-id>/nordea-frontend ./frontend
    ```

Note: In Backend, the entire project is used as the build context, and `-f backend/Dockerfile` means that the nested Dockerfile is used.
In Frontend, build context is only the `frontend` directory. In the future, consider updating Backend to also have a nested build context.
---

### Run the Docker Images (For local development purposes)
To run the Docker Image locally, use the following commands. 
The Backend API will be exposed at `http://localhost:8000/chat`,
and the Frontend will be accessible at `http://localhost:3000/`.

1. Run the backend container
    ```
    docker run -p 8000:8080 --name backend gcr.io/<your-project-id>/nordea-backend
    ```

2. Run the frontend container
    ```
    docker run -p 3000:3000 --name frontend gcr.io/chatbot-smart/nordea-frontend
    ```

The containers should now be accessible through the browser!
To stop the containers, run
    ```bash
    docker stop <container-name>
    ```
If you need to remove the container (and perhaps, build it again with changes), run
    ```bash
    docker rm <container-name>
    ```
---

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
