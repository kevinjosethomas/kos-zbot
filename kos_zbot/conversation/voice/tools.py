import json
import time
import base64
import tempfile
import subprocess
import os
from typing import Any, Dict, List
from pyee.asyncio import AsyncIOEventEmitter
from openai import OpenAI
import dotenv
import asyncio

dotenv.load_dotenv()


class ToolManager(AsyncIOEventEmitter):

    def __init__(self, robot=None, api_key=None):
        super().__init__()
        self.robot = robot
        self.connection = None

        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided either through constructor or OPENAI_API_KEY environment variable")

        from openai import AsyncOpenAI
        self.openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.openai.com/v1"
        )

    def set_connection(self, connection):
        self.connection = connection

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "wave",
                "description": "Make Z-Bot wave it's right hand. Use this whenever you want to greet the user, say goodbye to the user, or acknowledge a user's request to wave.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "type": "function",
                "name": "get_current_time",
                "description": "Get the current time of the day. Use this whenever the time will aid in the conversation, or to acknowledge a user's request to know the time.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "type": "function",
                "name": "describe_surroundings",
                "description": "Take a photo with the camera and describe what is visible in the surroundings",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    async def handle_tool_call(self, event):
        if not self.connection:
            print("No connection available for tool call")
            return False

        handlers = {
            "wave": self._handle_wave,
            "get_current_time": self._handle_get_current_time,
            "describe_surroundings": self._handle_describe_surroundings,
        }

        handler = handlers.get(event.name)
        if handler:
            await handler(event)
            return True
        else:
            print(f"Unknown tool: {event.name}")
            return False

    def capture_jpeg_cli(self, width: int = 640, height: int = 480, warmup_ms: int = 500) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            cmd = [
                "libcamera-jpeg",
                "-o", tmp.name,
                "-n",                # no preview, headless
                "--width", str(width),
                "--height", str(height),
                "-t", str(warmup_ms),
                "--nopreview",
                "--quality", "75"
            ]
            try:
                subprocess.run(cmd, check=True)
                tmp.seek(0)
                data = tmp.read()
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Camera capture failed: {e}")
            finally:
                os.remove(tmp.name)
            return data

    async def _handle_describe_surroundings(self, event):
        try:
            await self._create_tool_response(event.call_id, "Let me look...")
            
            jpeg_bytes = self.capture_jpeg_cli()
            base64_image = base64.b64encode(jpeg_bytes).decode('utf-8')
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this scene briefly, focusing only on the most important or interesting elements."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            description = response.choices[0].message.content.strip()
            await self._create_tool_response(event.call_id, f"I see {description}")
            
        except Exception as e:
            await self._create_tool_response(event.call_id, f"Sorry, I had trouble processing the image: {str(e)}")

    async def _handle_get_current_time(self, event):
        current_time = time.strftime("%I:%M %p")
        await self._create_tool_response(event.call_id, f"The current time is {current_time}.")

    async def _handle_wave(self, event):
        print("Wave requested")
        await self._create_tool_response(event.call_id, "Waving my right hand")

    async def _create_tool_response(self, call_id, output):
        if not self.connection:
            print("No connection available for tool response")
            return

        await self.connection.conversation.item.create(
            item={
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            }
        )
