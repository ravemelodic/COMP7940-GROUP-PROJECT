"""
Telegram Bot Agent - Handles user interactions and delegates tasks to workers
"""
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters, CommandHandler
from ChatGPT_HKBU import ChatGPT
from tasks import generate_video_task, analyze_document_task, analyze_image_task
import base64
import io
import configparser
import logging
import asyncpg
import os
import re
import asyncio

# Global variables
gpt = None
db_pool = None

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/comp7940-lab/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def init_db(config):
    """Initialize cloud database with connection pool"""
    global db_pool
    try:
        db_host = config['DATABASE']['HOST']
        db_name = config['DATABASE']['NAME']
        db_user = config['DATABASE']['USER']
        db_pwd = config['DATABASE']['PASSWORD']
        db_port = config['DATABASE']['PORT']

        # Create connection pool
        db_pool = await asyncpg.create_pool(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pwd,
            port=db_port,
            min_size=2,
            max_size=10
        )
        
        # Create tables if not exist
        async with db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        
        logger.info("Database pool initialized successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")


async def save_chat_log(user_id, user_msg, bot_reply):
    """Save chat log to database (async)"""
    if not db_pool:
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                '''
                INSERT INTO chat_logs (user_id, user_message, bot_response)
                VALUES ($1, $2, $3);
                ''',
                user_id, user_msg, bot_reply
            )
    except Exception as e:
        logger.error(f"Failed to save chat log: {e}")


async def search_course_info(keyword):
    """Search course information from database (async)"""
    global db_pool
    if db_pool is None:
        return ""

    try:
        async with db_pool.acquire() as conn:
            keyword = keyword.upper()
            
            # Query course info
            course = await conn.fetchrow(
                "SELECT course_name, class_time, location FROM courses WHERE course_code = $1",
                keyword
            )
            
            # Query assignments
            assignments = await conn.fetch(
                "SELECT title, deadline, description FROM assignments WHERE course_code = $1",
                keyword
            )
        
        info_str = f"Regarding {keyword}: \n"
        if course:
            info_str += f"- Course: {course['course_name']}, Time: {course['class_time']}, Location: {course['location']}\n"
        
        if assignments:
            info_str += "- Assignments: \n"
            for asn in assignments:
                info_str += f"  * {asn['title']} (Deadline: {asn['deadline']}), Requirement: {asn['description']}\n"
        
        return info_str if (course or assignments) else ""
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return ""
        logger.error(f"Database query error: {e}")
        return ""


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    logger.info(f"Received message from user {update.effective_user.id}")
    
    user_id = update.effective_user.id
    user_msg = update.message.text
    
    loading_message = await update.message.reply_text('Thinking...')

    course_code_match = re.search(r'[a-zA-Z]{4}\d{4}', user_msg)
    
    db_context = ""
    if course_code_match:
        course_code = course_code_match.group()
        db_context = await search_course_info(course_code)

    if db_context:
        final_prompt = f"Context from database:\n{db_context}\n\nStudent Question: {user_msg}"
    else:
        final_prompt = user_msg

    response = await gpt.submit(final_prompt)
    await save_chat_log(user_id, user_msg, response)
    await loading_message.edit_text(response)


async def handle_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    """Handler for /video command with optional prompt"""
    # Parse command arguments
    command_text = update.message.text.strip()
    parts = command_text.split(maxsplit=1)
    
    # Check if user provided prompt with command (e.g., /video 1, /video default)
    if len(parts) > 1:
        prompt_input = parts[1].strip()
        
        # Check if user has image stored
        image_base64 = context.user_data.get('video_image_base64')
        if not image_base64:
            await update.message.reply_text(
                "❌ No image found!\n\n"
                "Please send an image first, then use:\n"
                "• /video 1 (select first prompt)\n"
                "• /video 2 (select second prompt)\n"
                "• /video 3 (select third prompt)\n"
                "• /video default (smooth animation)\n"
                "• /video your custom prompt"
            )
            return
        
        # Process the prompt
        suggested_prompts = context.user_data.get('suggested_prompts', [])
        
        if prompt_input in ['1', '2', '3'] and suggested_prompts:
            try:
                prompt_index = int(prompt_input) - 1
                if 0 <= prompt_index < len(suggested_prompts):
                    user_prompt = suggested_prompts[prompt_index]
                    await update.message.reply_text(f"✅ Selected: {user_prompt}")
                else:
                    user_prompt = prompt_input
            except:
                user_prompt = prompt_input
        elif prompt_input.lower() == 'default':
            user_prompt = "smooth natural animation"
            await update.message.reply_text(f"✅ Using default prompt")
        else:
            user_prompt = prompt_input
            await update.message.reply_text(f"✅ Custom prompt: {user_prompt}")
        
        # Submit video generation task
        await handle_video_generation(update, context, image_base64, user_prompt)
        
        # Clean up stored data
        context.user_data.pop('video_image_base64', None)
        context.user_data.pop('suggested_prompts', None)
        context.user_data['waiting_for_video_prompt'] = False
        
    else:
        # No prompt provided, enter video mode
        await update.message.reply_text(
            "🎬 Image to Video Mode\n\n"
            "Step 1: Send me an image (photo or document)\n"
            "Step 2: After AI analysis, use:\n"
            "  • /video 1 (select first prompt)\n"
            "  • /video 2 (select second prompt)\n"
            "  • /video 3 (select third prompt)\n"
            "  • /video default (smooth animation)\n"
            "  • /video your custom prompt\n\n"
            "Send your image now!"
        )
        
        context.user_data['waiting_for_video_image'] = True
        context.user_data['waiting_for_video_prompt'] = False


async def handle_document_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document/image uploads"""
    # Check if user is in video mode
    if context.user_data.get('waiting_for_video_image'):
        context.user_data['waiting_for_video_image'] = False
        
        # Get image file
        if update.message.photo:
            photo = update.message.photo[-1]
            file = await photo.get_file()
        elif update.message.document:
            file = await update.message.document.get_file()
        else:
            await update.message.reply_text("❌ Please send an image file.")
            return
        
        await update.message.reply_text(
            "✅ Image received!\n\n"
            "🤖 AI is analyzing your image in the background...\n"
            "💬 You can continue chatting with me while waiting!\n\n"
            "I'll notify you when analysis is complete."
        )
        
        # Process image analysis in background
        asyncio.create_task(process_image_analysis(update, context, file))
        
        return
    
    # Handle document analysis (PDF only, no OCR for images)
    if update.message.document:
        file = update.message.document
        file_name = file.file_name or "document"
        
        # Check if it's a PDF
        if not file_name.lower().endswith('.pdf'):
            await update.message.reply_text(
                "📄 Document Analysis\n\n"
                "Currently only PDF files are supported.\n"
                "For images, please use the /video command for image-to-video conversion."
            )
            return
        
        await update.message.reply_text(
            "📄 Document Analysis Started\n\n"
            "⏳ Processing your PDF in the background...\n"
            "💬 You can continue chatting with me while waiting!\n\n"
            "I'll send you the summary when it's ready (usually 1-2 minutes)."
        )
        
        # Process document analysis in background
        asyncio.create_task(process_document_analysis(update, context, file, file_name))
        
        return
    
    # If it's just a photo (not in video mode and not a document)
    await update.message.reply_text(
        "📸 Image received!\n\n"
        "To convert this image to video, please use the /video command first."
    )


async def process_image_analysis(update, context, file):
    """Process image analysis in background (non-blocking)"""
    user_id = update.effective_user.id
    
    try:
        # Download image to memory and convert to base64
        image_bytes = io.BytesIO()
        await file.download_to_memory(image_bytes)
        image_bytes.seek(0)
        
        image_base64_data = base64.b64encode(image_bytes.read()).decode('utf-8')
        
        file_path = file.file_path or ""
        if file_path.lower().endswith('.png'):
            mime_type = 'image/png'
        elif file_path.lower().endswith('.gif'):
            mime_type = 'image/gif'
        elif file_path.lower().endswith('.webp'):
            mime_type = 'image/webp'
        else:
            mime_type = 'image/jpeg'
        
        image_base64 = f"data:{mime_type};base64,{image_base64_data}"
        
        # Store base64 for later use
        context.user_data['video_image_base64'] = image_base64
        
        # Submit image analysis task to worker (non-blocking)
        task = analyze_image_task.apply_async(
            args=[image_base64, user_id],
            queue='ocr'
        )
        
        # Wait for result in background
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: task.get(timeout=60)
        )
        
        if result['success']:
            ai_response = result['analysis']
            suggested_prompts = result.get('suggested_prompts', [])
            
            if suggested_prompts:
                context.user_data['suggested_prompts'] = suggested_prompts
            
            # Save image analysis log
            try:
                await save_chat_log(
                    user_id,
                    "[Image Analysis Request]",
                    f"AI Analysis: {ai_response[:200]}..."
                )
            except Exception as log_e:
                logger.error(f"Failed to save image analysis log: {log_e}")
            
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Image Analysis Complete!\n\n"
                    f"🤖 AI Analysis:\n{ai_response}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "Now use one of these commands:\n"
                    "• /video 1 (select first prompt)\n"
                    "• /video 2 (select second prompt)\n"
                    "• /video 3 (select third prompt)\n"
                    "• /video default (smooth animation)\n"
                    "• /video your custom prompt"
                )
            )
        else:
            raise Exception(result.get('error', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Image analysis error: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "⚠️ Image analysis completed with limited info.\n\n"
                "You can still generate video using:\n"
                "• /video default (smooth animation)\n"
                "• /video your custom prompt\n\n"
                "Examples:\n"
                "• /video smooth zoom in effect\n"
                "• /video gentle camera pan from left to right"
            )
        )


async def process_document_analysis(update, context, file, file_name):
    """Process document analysis in background (non-blocking)"""
    user_id = update.effective_user.id
    temp_file_path = f"/comp7940-lab/temp/doc_{user_id}_{file.file_unique_id}.pdf"
    
    try:
        # Get file object and download
        telegram_file = await file.get_file()
        await telegram_file.download_to_drive(temp_file_path)
        
        # Submit document analysis task to worker (non-blocking)
        task = analyze_document_task.apply_async(
            args=[temp_file_path, 'pdf', user_id],
            queue='ocr'
        )
        
        # Wait for result in background
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: task.get(timeout=180)
        )
        
        if result['success']:
            summary = result['summary']
            
            # Save document analysis log
            try:
                await save_chat_log(
                    user_id,
                    f"[Document]: {file_name}",
                    summary
                )
                logger.info(f"Saved document analysis log for user {user_id}")
            except Exception as log_e:
                logger.error(f"Failed to save document log: {log_e}")
            
            # Send summary
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"📝 **Document Analysis Result**\n\n"
                    f"📄 File: {file_name}\n\n"
                    f"{summary}"
                )
            )
        else:
            error_msg = result.get('error', 'Unknown error')
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ Document analysis failed\n\n"
                    f"Error: {error_msg}\n\n"
                    f"Please try again or contact support."
                )
            )
            
    except Exception as e:
        logger.error(f"Document analysis error: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ An error occurred during document analysis\n\n"
                f"Error: {str(e)}\n\n"
                f"Please try again later."
            )
        )
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temp file: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to delete temp file: {e}")


async def handle_video_generation(update, context, image_base64, user_prompt):
    """Handle video generation by submitting task to worker"""
    user_id = update.effective_user.id
    output_video = f"/comp7940-lab/temp/output_video_{user_id}.mp4"
    
    try:
        # Submit video generation task to worker
        task = generate_video_task.apply_async(
            args=[image_base64, user_prompt, user_id, output_video],
            queue='video'
        )
        
        # Store task ID for later retrieval
        context.user_data['video_task_id'] = task.id
        
        await update.message.reply_text(
            "🎬 Video generation started!\n"
            f"Prompt: {user_prompt}\n\n"
            "✅ Your video is being processed in the background.\n"
            "⏱️ This usually takes 2-10 minutes.\n"
            "📬 I'll send you the video when it's ready!\n\n"
            "💬 You can continue chatting with me while waiting."
        )
        
        # Start background task to monitor progress
        asyncio.create_task(monitor_video_task(update, context, task, output_video, user_prompt))
        
    except Exception as e:
        logger.error(f"Video generation error: {str(e)}")
        await update.message.reply_text(
            f"❌ An error occurred during video generation:\n{str(e)}"
        )


async def monitor_video_task(update, context, task, output_video, user_prompt):
    """Monitor video generation task in background"""
    user_id = update.effective_user.id
    last_status = None
    
    try:
        # Wait for task to complete
        while not task.ready():
            task_info = task.info
            if isinstance(task_info, dict):
                status = task_info.get('status')
                position = task_info.get('position', 0)
                
                # Only send update if status changed
                if status != last_status and status in ["InQueue", "InProgress"]:
                    last_status = status
                    
                    status_emoji = {
                        "InQueue": "⏳",
                        "InProgress": "🎬"
                    }
                    
                    emoji = status_emoji.get(status, "🔄")
                    
                    if status == "InQueue":
                        message = f"{emoji} Your video is queued (Position: {position})"
                    else:
                        message = f"{emoji} Your video is being processed..."
                    
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message
                        )
                    except:
                        pass
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
        # Get result
        result = task.get()
        
        if result['success'] and os.path.exists(output_video):
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Video generated! Uploading..."
            )
            
            with open(output_video, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=user_id,
                    video=video_file,
                    caption=f"🎥 Your generated video is ready!\nPrompt: {user_prompt}",
                    supports_streaming=True
                )
            
            # Save success log to database
            try:
                await save_chat_log(user_id, f"[Video Prompt]: {user_prompt}", "Video generated successfully")
                logger.info(f"Saved video generation log for user {user_id}")
            except Exception as log_e:
                logger.error(f"Failed to save video log: {log_e}")
            
            # Clean up
            try:
                os.remove(output_video)
                logger.info(f"Cleaned up video file: {output_video}")
            except Exception as e:
                logger.error(f"Failed to delete video file: {e}")
        else:
            error_msg = result.get('error', 'Unknown error')
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Video generation failed: {error_msg}\n\nPlease try again later."
            )
            
            # Save failure log to database
            try:
                await save_chat_log(user_id, f"[Video Prompt]: {user_prompt}", f"Failed: {error_msg}")
                logger.info(f"Saved video failure log for user {user_id}")
            except Exception as log_e:
                logger.error(f"Failed to save video failure log: {log_e}")
            
    except Exception as e:
        logger.error(f"Video monitoring error: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ An error occurred: {str(e)}\n\nPlease try again later."
        )
        
        # Save error log to database
        try:
            await save_chat_log(user_id, f"[Video Prompt]: {user_prompt}", f"Error: {str(e)}")
        except:
            pass


# Application initialization
async def init_app():
    """Initialize and return the bot application"""
    logger.info("Initializing Telegram Bot Agent...")
    
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Initialize database (async)
    await init_db(config)
    
    # Create bot application
    app = ApplicationBuilder().token(config['TELEGRAM']['ACCESS_TOKEN']).build()
    
    global gpt
    gpt = ChatGPT(config)
    
    # Register handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, callback))
    app.add_handler(CommandHandler('video', lambda update, context: handle_video_command(update, context, config)))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.PDF | filters.Document.IMAGE, handle_document_summary))
    
    logger.info("Bot agent initialized successfully!")
    return app


# Entry point for Docker container
if __name__ == '__main__':
    async def main():
        app = await init_app()
        
        # Run the bot
        async with app:
            await app.start()
            await app.updater.start_polling()
            
            # Keep running until interrupted
            try:
                await asyncio.Event().wait()
            except (KeyboardInterrupt, SystemExit):
                logger.info("Shutting down bot...")
            finally:
                await app.updater.stop()
                await app.stop()
                
                # Close database pool
                if db_pool:
                    await db_pool.close()
                
                # Close ChatGPT client
                if gpt:
                    await gpt.close()
    
    asyncio.run(main())
