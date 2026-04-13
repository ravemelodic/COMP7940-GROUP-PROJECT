"""
Task definitions for Celery workers
"""
from celery import Celery
import os
import sys
import logging
import configparser

# Add current directory to Python path
sys.path.insert(0, '/comp7940-lab')

# Import project modules
from ChatGPT_HKBU import ChatGPT
from image_to_video import ImageToVideoGenerator

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Celery
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
celery_app = Celery(
    'chatbot_tasks',
    broker=f'redis://{redis_host}:{redis_port}/0',
    backend=f'redis://{redis_host}:{redis_port}/0'
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 60 minutes hard limit (3600 seconds)
    task_soft_time_limit=3540,  # 59 minutes soft limit (3540 seconds)
)


@celery_app.task(name='tasks.generate_video', bind=True)
def generate_video_task(self, image_base64, prompt, user_id, output_path):
    """
    Task to generate video from image
    
    Args:
        image_base64: Base64 encoded image
        prompt: Video generation prompt
        user_id: Telegram user ID
        output_path: Path to save output video
    
    Returns:
        dict: Result with success status and video path or error
    """
    logger.info(f"Starting video generation task for user {user_id}")
    
    try:
        # Load config
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Initialize generator
        generator = ImageToVideoGenerator(config)
        
        # Define status callback to update task state
        def status_callback(status, position):
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': status,
                    'position': position,
                    'user_id': user_id
                }
            )
        
        # Generate video
        success = generator.generate_and_wait(
            image_base64=image_base64,
            output_path=output_path,
            prompt=prompt,
            image_size="1280x720",
            max_wait_time=3000,
            status_callback=status_callback
        )
        
        if success:
            logger.info(f"Video generation completed for user {user_id}")
            return {
                'success': True,
                'video_path': output_path,
                'user_id': user_id
            }
        else:
            logger.error(f"Video generation failed for user {user_id}")
            return {
                'success': False,
                'error': 'Video generation failed',
                'user_id': user_id
            }
            
    except Exception as e:
        logger.error(f"Video generation error for user {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }


@celery_app.task(name='tasks.analyze_document', bind=True)
def analyze_document_task(self, file_path, file_type, user_id):
    """
    Task to analyze document (PDF or image) with OCR
    
    Args:
        file_path: Path to the document file
        file_type: Type of file ('pdf' or 'image')
        user_id: Telegram user ID
    
    Returns:
        dict: Result with extracted text and summary
    """
    logger.info(f"Starting document analysis task for user {user_id}")
    
    try:
        import fitz  # PyMuPDF
        
        # Load config
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        extracted_text = ""
        
        # Update task state
        self.update_state(state='PROGRESS', meta={'status': 'extracting_text'})
        
        # Extract text based on file type
        if file_type == 'pdf':
            doc = fitz.open(file_path)
            for page in doc[:5]:  # First 5 pages
                extracted_text += page.get_text()
            doc.close()
        else:  # image
            # Without EasyOCR, we can't process images
            return {
                'success': False,
                'error': 'Image OCR not available (EasyOCR not installed)',
                'user_id': user_id
            }
        
        # Update task state
        self.update_state(state='PROGRESS', meta={'status': 'generating_summary'})
        
        # Generate summary with ChatGPT
        if len(extracted_text.strip()) > 50:
            gpt = ChatGPT(config)
            prompt = (
                f"You are a professional academic assistant. Please read the following content "
                f"extracted from an educational document and provide a concise summary including: "
                f"1. Core Course Objectives, 2. Key Deadlines/Tasks, and 3. Important Requirements/Knowledge Points.\n\n"
                f"Content:\n{extracted_text[:3000]}"
            )
            # Use sync method in worker
            summary = gpt.submit_sync(prompt)
        else:
            summary = "Could not extract enough text from the document."
        
        logger.info(f"Document analysis completed for user {user_id}")
        
        return {
            'success': True,
            'summary': summary,
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"Document analysis error for user {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }


@celery_app.task(name='tasks.analyze_image', bind=True)
def analyze_image_task(self, image_base64, user_id):
    """
    Task to analyze image with GPT and suggest video prompts
    
    Args:
        image_base64: Base64 encoded image
        user_id: Telegram user ID
    
    Returns:
        dict: Result with AI analysis and suggested prompts
    """
    logger.info(f"Starting image analysis task for user {user_id}")
    
    try:
        # Load config
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Initialize ChatGPT
        gpt = ChatGPT(config)
        
        # Analyze image
        ai_prompt = (
            "Analyze this image and provide:\n"
            "1. A brief description of what you see (1-2 sentences)\n"
            "2. Three creative video animation prompt suggestions that would work well with this image\n\n"
            "Format your response as:\n"
            "Description: [your description]\n\n"
            "Suggested prompts:\n"
            "1. [prompt 1]\n"
            "2. [prompt 2]\n"
            "3. [prompt 3]"
        )
        
        # Use sync method in worker
        ai_response = gpt.submit_with_image_sync(ai_prompt, image_base64, use_image_analysis_prompt=True)
        
        # Extract suggested prompts
        suggested_prompts = []
        lines = ai_response.split('\n')
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.')):
                prompt_text = line.split('.', 1)[1].strip()
                if prompt_text:
                    suggested_prompts.append(prompt_text)
        
        logger.info(f"Image analysis completed for user {user_id}")
        
        return {
            'success': True,
            'analysis': ai_response,
            'suggested_prompts': suggested_prompts,
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"Image analysis error for user {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }
