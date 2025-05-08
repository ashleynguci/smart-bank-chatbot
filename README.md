# Smart Bank Chatbot
A conversational AI assistant tailored for smart banking operations built during a weekend Hackathon.

## Getting Started

Follow these steps to set up and run the application:

### Prerequisites

Ensure you have the following installed:
- Python 3.8 or higher
- `pip` (Python package manager)
- **Docker** (For building and deploying the backend API)
- **Google Cloud SDK** (For deploying to Google Cloud)

Also, ensure you have access to your Google Cloud project.

### API Keys 🔑 
Get your Gemini API key from: [Google AI Studio](https://aistudio.google.com/app/apikey)  
Get your Tavily API key from: [Tavily dashboard](https://app.tavily.com/home)

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/ashleynguci/smart-bank-chatbot.git
    cd smart-bank-chatbot
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

---

## Docker: Build and Deploy Backend API

This section will guide you on how to build and deploy the backend API to **Google Cloud Run** using **Docker**.

### Build the Docker Image

1. **Navigate to the root directory** where the `Dockerfile` is located:
    ```bash
    cd smart-bank-chatbot
    ```

2. **Build the Docker image** using the following command:
    ```bash
    docker build -t gcr.io/<your-project-id>/nordea-backend .
    ```

    - Replace `<your-project-id>` with your actual Google Cloud project ID. This command builds the Docker image as per the `Dockerfile` in your `backend` directory.

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


### Test the Deployed API

Once the backend API is deployed, you can test the `/chat` API endpoint by sending a **POST** request to it. You can use **Postman** or **curl** for testing.

Example using `curl`:
```bash
curl -X 'POST' \
  'https://<your-service-name>.run.app/chat' \
  -H 'Content-Type: application/json' \
  -d '{
  "input": "Hello, do I have any unpaid invoice?"
}'
