import httpx
import configparser


# An async client for the ChatGPT REST API
class ChatGPT:
    def __init__(self, config):
        # Read API configuration values from the ini file
        api_key = config['CHATGPT']['API_KEY']
        base_url = config['CHATGPT']['BASE_URL']
        model = config['CHATGPT']['MODEL']
        api_ver = config['CHATGPT']['API_VER']

        # Construct the full REST endpoint URL for chat completions
        self.url = f'{base_url}/deployments/{model}/chat/completions?api-version={api_ver}'

        # Set HTTP headers required for authentication and JSON payload
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "api-key": api_key,
        }

        # Define the system prompt to guide the assistant's behavior
        self.system_message = (
            "You are a multifunctional assistant for HKBU students. "
            "Your capabilities include:\n"
            "1. Course & Assignment Helper: When the user mentions a course code (e.g., COMP7940), you will receive database information (course time, location, assignment deadlines, requirements). Always prioritize that data. If no database info is available, answer generally without inventing specific course details.\n"
            "2. Image-to-Video Generation: The bot supports converting an image into an animated video. Guide the user to use the /video command: send /video, then upload an image, then provide an animation prompt (or type 'default' for smooth natural animation). The video will be generated in the background and sent when ready.\n"
            "3. Document Analysis: The bot can quickly extract text from PDFs (direct text extraction, no OCR, fast) and provide concise summaries. For images with embedded text, basic extraction is supported. This feature is ready and efficient.\n"
            "Keep responses clear, concise, and student-friendly. If a user asks something outside these capabilities, answer politely or suggest using the available features."
        )
        
        # System message for image analysis
        self.image_analysis_message = (
            "You are an expert at analyzing images and suggesting creative video animation prompts. "
            "Describe what you see in the image briefly, then suggest 3 specific video animation prompts "
            "that would work well with this image. Focus on camera movements, transitions, and effects."
        )
        
        # Create async HTTP client (will be reused for all requests)
        self.client = None
        # Create sync HTTP client for worker tasks
        self.sync_client = None

    def _get_client(self):
        """Get or create async HTTP client"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client
    
    def _get_sync_client(self):
        """Get or create sync HTTP client"""
        if self.sync_client is None:
            self.sync_client = httpx.Client(timeout=60.0)
        return self.sync_client
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
        if self.sync_client:
            self.sync_client.close()
            self.sync_client = None

    async def submit(self, user_message: str):
        """
        Submit a text message to ChatGPT (async)
        
        Args:
            user_message: Text message to send
        
        Returns:
            str: Assistant's reply
        """
        # Build the conversation history: system + user message
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message},
        ]

        # Prepare the request payload with generation parameters
        payload = {
            "messages": messages,
            "temperature": 1,  # randomness of output (higher = more creative)
            "max_tokens": 150,  # maximum length of the reply
            "top_p": 1,  # nucleus sampling parameter
            "stream": False  # disable streaming, wait for full reply
        }

        # Send the async request to the ChatGPT REST API
        client = self._get_client()
        response = await client.post(self.url, json=payload, headers=self.headers)

        # If successful, return the assistant's reply text
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Otherwise return error details
            return "Error: " + response.text
    
    def submit_sync(self, user_message: str):
        """
        Submit a text message to ChatGPT (sync version for workers)
        
        Args:
            user_message: Text message to send
        
        Returns:
            str: Assistant's reply
        """
        # Build the conversation history: system + user message
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message},
        ]

        # Prepare the request payload with generation parameters
        payload = {
            "messages": messages,
            "temperature": 1,
            "max_tokens": 150,
            "top_p": 1,
            "stream": False
        }

        # Send the sync request to the ChatGPT REST API
        client = self._get_sync_client()
        response = client.post(self.url, json=payload, headers=self.headers)

        # If successful, return the assistant's reply text
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Otherwise return error details
            return "Error: " + response.text
    
    async def submit_with_image(self, user_message: str, image_base64: str, use_image_analysis_prompt: bool = False):
        """
        Submit a message with an image (base64 encoded) - async version
        
        Args:
            user_message: Text message to send
            image_base64: Base64 encoded image data URI (e.g., "data:image/jpeg;base64,XXX")
            use_image_analysis_prompt: Use specialized prompt for image analysis
        
        Returns:
            str: Assistant's reply
        """
        # Choose system message
        system_msg = self.image_analysis_message if use_image_analysis_prompt else self.system_message
        
        # Build the conversation with image content
        messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64,
                            "detail": "low"  # Use low detail for faster processing
                        }
                    }
                ]
            }
        ]

        # Prepare the request payload
        payload = {
            "messages": messages,
            "temperature": 1,  # Use default value (required by this model)
            "max_tokens": 300,
            "top_p": 1,
            "stream": False
        }

        # Send the async request to the ChatGPT REST API
        client = self._get_client()
        response = await client.post(self.url, json=payload, headers=self.headers)

        # If successful, return the assistant's reply text
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Otherwise return error details
            return "Error: " + response.text
    
    def submit_with_image_sync(self, user_message: str, image_base64: str, use_image_analysis_prompt: bool = False):
        """
        Submit a message with an image (base64 encoded) - sync version for workers
        
        Args:
            user_message: Text message to send
            image_base64: Base64 encoded image data URI (e.g., "data:image/jpeg;base64,XXX")
            use_image_analysis_prompt: Use specialized prompt for image analysis
        
        Returns:
            str: Assistant's reply
        """
        # Choose system message
        system_msg = self.image_analysis_message if use_image_analysis_prompt else self.system_message
        
        # Build the conversation with image content
        messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64,
                            "detail": "low"
                        }
                    }
                ]
            }
        ]

        # Prepare the request payload
        payload = {
            "messages": messages,
            "temperature": 1,
            "max_tokens": 300,
            "top_p": 1,
            "stream": False
        }

        # Send the sync request to the ChatGPT REST API
        client = self._get_sync_client()
        response = client.post(self.url, json=payload, headers=self.headers)

        # If successful, return the assistant's reply text
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Otherwise return error details
            return "Error: " + response.text


if __name__ == '__main__':
    # Entry point for standalone testing
    import configparser
    import asyncio
    
    async def main():
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        chatGPT = ChatGPT(config)
        
        print("ChatGPT HKBU Client - Test Mode (Async)")
        print("Type 'exit' to quit\n")
        
        try:
            while True:
                user_input = input('Query: ').strip()
                if user_input.lower() == 'exit':
                    break
                if user_input:
                    response = await chatGPT.submit(user_input)
                    print(f"Response: {response}\n")
        finally:
            await chatGPT.close()
    
    asyncio.run(main())
