"""
Context Builder - Builds conversation context with memory retrieval.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from memory.models import (
    UserProfile, UserPreferences, UserGoal, UserProject,
    ImportantPerson, UsefulFact, ConversationSummary
)
from memory.memory_interface import MemoryInterface
from personality.personality_engine import PersonalityEngine


@dataclass
class ConversationMessage:
    """Single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentContext:
    """Complete context for agent decision making."""
    user_profile: Optional[UserProfile] = None
    user_preferences: Optional[UserPreferences] = None
    recent_messages: List[ConversationMessage] = field(default_factory=list)
    relevant_goals: List[UserGoal] = field(default_factory=list)
    relevant_projects: List[UserProject] = field(default_factory=list)
    relevant_people: List[ImportantPerson] = field(default_factory=list)
    relevant_facts: List[UsefulFact] = field(default_factory=list)
    conversation_summaries: List[ConversationSummary] = field(default_factory=list)
    system_prompt: str = ""
    session_id: str = ""
    current_topic: str = ""


class ContextBuilder:
    """Builds rich context for the agent from memory and conversation history."""
    
    def __init__(self, memory: MemoryInterface, personality: PersonalityEngine):
        self.memory = memory
        self.personality = personality
        self._message_history: List[ConversationMessage] = []
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_topic = ""
    
    def build_context(self, user_input: str, max_messages: int = 10) -> AgentContext:
        """Build complete context for current turn."""
        
        # Get user profile and preferences
        profile = self.memory.get_user_profile()
        prefs = self.memory.get_user_preferences()
        
        # Build system prompt with personality
        system_prompt = self.personality.build_system_prompt(profile, prefs)
        
        # Retrieve relevant memory based on user input
        relevant_facts = self.memory.search_facts(user_input, limit=5)
        relevant_goals = self.memory.search_goals(user_input, limit=3)
        relevant_projects = self.memory.search_projects(user_input, limit=3)
        relevant_people = self.memory.get_important_people()[:5]
        
        # Get recent conversation summaries for long-term context
        conversation_summaries = self.memory.get_recent_context(limit=3)
        
        # Build context object
        context = AgentContext(
            user_profile=profile,
            user_preferences=prefs,
            recent_messages=self._message_history[-max_messages:],
            relevant_goals=relevant_goals,
            relevant_projects=relevant_projects,
            relevant_people=relevant_people,
            relevant_facts=relevant_facts,
            conversation_summaries=conversation_summaries,
            system_prompt=system_prompt,
            session_id=self._session_id,
            current_topic=self._current_topic
        )
        
        return context
    
    def add_message(self, role: str, content: str, 
                   tool_calls: List[Dict[str, Any]] = None,
                   tool_results: List[Dict[str, Any]] = None) -> None:
        """Add message to conversation history."""
        msg = ConversationMessage(
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            tool_results=tool_results or []
        )
        self._message_history.append(msg)
    
    def get_conversation_history(self, limit: int = 20) -> List[ConversationMessage]:
        """Get recent conversation history."""
        return self._message_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear conversation history (new session)."""
        self._message_history.clear()
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_topic = ""
    
    def set_topic(self, topic: str) -> None:
        """Set current conversation topic."""
        self._current_topic = topic
    
    def format_context_for_llm(self, context: AgentContext) -> str:
        """Format context into a prompt for the LLM."""
        parts = []
        
        # System prompt
        parts.append(context.system_prompt)
        parts.append("")
        
        # Relevant memory context
        if context.relevant_facts:
            parts.append("RELEVANT FACTS:")
            for fact in context.relevant_facts:
                parts.append(f"  - [{fact.category}] {fact.fact}")
            parts.append("")
        
        if context.relevant_goals:
            parts.append("ACTIVE GOALS:")
            for goal in context.relevant_goals:
                parts.append(f"  - {goal.title} ({goal.status.value})")
            parts.append("")
        
        if context.relevant_projects:
            parts.append("CURRENT PROJECTS:")
            for project in context.relevant_projects:
                parts.append(f"  - {project.name} ({project.status.value})")
            parts.append("")
        
        if context.relevant_people:
            parts.append("IMPORTANT PEOPLE:")
            for person in context.relevant_people:
                parts.append(f"  - {person.name} ({person.relationship})")
            parts.append("")
        
        # Conversation history
        if context.recent_messages:
            parts.append("RECENT CONVERSATION:")
            for msg in context.recent_messages:
                prefix = "User" if msg.role == "user" else "Ashu"
                parts.append(f"{prefix}: {msg.content}")
            parts.append("")
        
        # Current input placeholder
        parts.append("User: {user_input}")
        parts.append("Ashu:")
        
        return "\n".join(parts)
    
    def create_summary_prompt(self, messages: List[ConversationMessage]) -> str:
        """Create prompt for summarizing conversation."""
        conversation_text = "\n".join([
            f"{'User' if m.role == 'user' else 'Ashu'}: {m.content}"
            for m in messages
        ])
        
        return f"""Summarize this conversation in 2-3 sentences. Focus on:
- Main topics discussed
- Any decisions made or actions agreed
- User's emotional state/needs
- Key facts revealed

Conversation:
{conversation_text}

Summary:"""
    
    def extract_key_topics(self, messages: List[ConversationMessage]) -> List[str]:
        """Extract key topics from messages (simple keyword extraction)."""
        # Simple implementation - in production use NLP/embeddings
        text = " ".join([m.content.lower() for m in messages])
        
        # Common topic keywords
        topic_keywords = {
            "work": ["work", "job", "office", "meeting", "project", "deadline", "boss", "colleague"],
            "study": ["study", "exam", "assignment", "homework", "college", "university", "learn", "course"],
            "health": ["health", "sick", "doctor", "hospital", "medicine", "pain", "tired", "stress", "anxiety"],
            "relationships": ["friend", "family", "girlfriend", "boyfriend", "partner", "parents", "mother", "father", "sister", "brother"],
            "entertainment": ["movie", "series", "game", "music", "instagram", "reels", "youtube", "netflix", "bore"],
            "finance": ["money", "salary", "expense", "budget", "save", "invest", "loan", "rent", "emi"],
            "goals": ["goal", "target", "achieve", "plan", "future", "career", "dream", "wish"],
            "daily_life": ["food", "sleep", "exercise", "gym", "walk", "cook", "clean", "shopping", "travel"],
        }
        
        found_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                found_topics.append(topic)
        
        return found_topics[:5]  # Top 5 topics