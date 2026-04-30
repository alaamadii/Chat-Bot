import uuid
from typing import Dict, List, Optional
from intake.models import NormalizedMessage

class SessionManager:
    def __init__(self):
        # Maps user_id to session_id
        self._user_sessions: Dict[str, str] = {}
        # Maps session_id to list of messages
        self._history: Dict[str, List[NormalizedMessage]] = {}

    def get_or_create_session(self, user_id: str) -> str:
        """
        Returns the active session ID for a user, or creates a new one.
        """
        if user_id in self._user_sessions:
            return self._user_sessions[user_id]
        
        # Create new session
        new_session_id = str(uuid.uuid4())
        self._user_sessions[user_id] = new_session_id
        self._history[new_session_id] = []
        return new_session_id

    def add_message(self, message: NormalizedMessage):
        """
        Adds a message to the session history.
        """
        session_id = message.session_id
        if session_id not in self._history:
            self._history[session_id] = []
        
        self._history[session_id].append(message)

    def get_history(self, session_id: str) -> List[NormalizedMessage]:
        """
        Retrieves the conversation history for a session.
        """
        return self._history.get(session_id, [])

# Global in-memory instance for simplicity
session_manager = SessionManager()
