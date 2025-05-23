import base64
import asyncio
from openai import AsyncOpenAI
from .tools import ToolManager
from pyee.asyncio import AsyncIOEventEmitter

SYSTEM_PROMPT = """You are ZBot, a friendly and helpful voice assistant robot. You have a warm, engaging personality and always aim to be helpful while maintaining a natural conversation flow. 

Key characteristics:
- You are a robot named ZBot, and you should acknowledge this in your first interaction
- You should mention that you're here to help the user today
- You speak in a friendly, conversational tone
- You're concise and clear in your responses
- You always speak in English unless explicitly asked otherwise
- You can show personality while staying professional
- You're knowledgeable but humble
- You can make appropriate jokes or light-hearted comments when appropriate
- You're always ready to help with tasks or answer questions

Remember to:
- Keep responses brief and to the point
- Use natural language and contractions
- Be friendly but not overly casual
- Show enthusiasm when appropriate
- Admit when you don't know something
- Maintain a helpful and positive attitude
- Always start your first interaction with: "Hello! I'm ZBot, your personal robot. I'm here to help you today. How can I assist you?" """

class AudioProcessor(AsyncIOEventEmitter):
    """Processes audio through OpenAI's API.

    This class handles the communication with OpenAI's API for speech processing.
    It acts as the bridge between the AudioRecorder and AudioPlayer components.

    Attributes:
        client (AsyncOpenAI): OpenAI API client for async communication
        connection (AsyncRealtimeConnection): Active connection to OpenAI API
        session: Current voice session for maintaining conversation state
        robot: Reference to the main robot instance
        connected (asyncio.Event): Event flag indicating active API connection
        tool_manager (ToolManager): Manages LLM tools including vision capabilities

    Events emitted:
        - audio_to_play: When processed audio is ready to be played
        - processing_complete: When audio processing is complete
        - set_volume: When volume change is requested
        - session_ready: When the OpenAI session is initialized and ready
    """

    def __init__(
        self,
        openai_api_key,
        robot=None,
    ):
        super().__init__()
        self.robot = robot
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.connection = None
        self.session = None
        self.connected = asyncio.Event()

        self.tool_manager = ToolManager(robot=robot, api_key=openai_api_key)

        self.tool_manager.on(
            "set_volume", lambda volume: self.emit("set_volume", volume)
        )

    async def connect(self):
        async with self.client.beta.realtime.connect(
            model="gpt-4o-mini-realtime-preview"
        ) as conn:
            self.connection = conn
            self.connected.set()

            self.tool_manager.set_connection(conn)

            print("Connected to OpenAI")

            async for event in conn:
                if event.type == "session.created":
                    print("Session created")
                    await self._handle_session_created(conn)
                elif event.type == "session.updated":
                    self.session = event.session
                elif event.type == "response.audio.delta":
                    await self._handle_audio_delta(event)
                elif event.type == "response.done":
                    self.emit("processing_complete")
                elif event.type == "response.function_call_arguments.done":
                    await self._handle_tool_call(conn, event)
                    await conn.response.create()
                elif event.type == "error":
                    print(event.error)

    async def _handle_session_created(self, conn):
        self.session = conn.session
        tools = self.tool_manager.get_tool_definitions()

        await conn.session.update(
            session={
                "voice": "echo",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.7,
                },
                "tools": tools,
                "instructions": SYSTEM_PROMPT,
            }
        )

        self.emit("session_ready")

    async def process_audio(self, audio_bytes):
        if not self.connected.is_set():
            print("Not connected to OpenAI API")
            return

        connection = self.connection
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        await connection.input_audio_buffer.append(audio=audio_b64)

    async def _handle_audio_delta(self, event):
        audio_bytes = base64.b64decode(event.delta)
        self.emit("audio_to_play", audio_bytes)

    async def _handle_tool_call(self, conn, event):
        await self.tool_manager.handle_tool_call(event)

    def cancel_response(self):
        if self.connection:
            asyncio.create_task(
                self.connection.send({"type": "response.cancel"})
            )
