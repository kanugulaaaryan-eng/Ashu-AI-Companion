"""
Decision Engine - Determines what action Ashu should take.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from brain.context import AgentContext, ConversationMessage
from memory.models import UserGoal, UserProject
from tools.tool_system import ToolSystem, ToolResult


class ActionType(Enum):
    """Types of actions Ashu can take."""
    ANSWER = "answer"           # Just respond conversationally
    REMEMBER = "remember"       # Store something in memory
    SUGGEST = "suggest"         # Proactive suggestion
    ASK_FOLLOWUP = "ask_followup"  # Ask clarifying question
    USE_TOOL = "use_tool"       # Execute a tool
    ONBOARDING = "onboarding"   # Onboarding flow
    SUMMARIZE = "summarize"     # Summarize conversation


@dataclass
class AgentDecision:
    """Decision made by the agent."""
    action_type: ActionType
    response: str = ""
    tool_name: str = ""
    tool_args: Dict[str, Any] = None
    memory_updates: List[Dict[str, Any]] = None
    suggestions: List[str] = None
    followup_question: str = ""
    confidence: float = 1.0
    reasoning: str = ""
    
    def __post_init__(self):
        if self.tool_args is None:
            self.tool_args = {}
        if self.memory_updates is None:
            self.memory_updates = []
        if self.suggestions is None:
            self.suggestions = []


class DecisionEngine:
    """Engine for deciding what action to take based on context."""
    
    def __init__(self, tool_system: 'ToolSystem'):
        self.tool_system = tool_system
        self._decision_keywords = {
            ActionType.REMEMBER: [
                "remember", "note down", "save this", "keep in mind",
                "yad rakho", "save", "store", "memorize"
            ],
            ActionType.USE_TOOL: [
                "create", "write", "make", "set timer", "remind me",
                "open", "search", "find", "calculate", "note"
            ],
            ActionType.SUGGEST: [
                "bored", "bore", "nothing to do", "suggest", "recommend",
                "what should i do", "ideas", "plan"
            ],
            ActionType.ASK_FOLLOWUP: [
                "?", "how", "what", "why", "when", "where", "who",
                "enti", "ela", "ekkada", "eppudu", "enduku"
            ],
        }
    
    def decide(self, context: AgentContext, user_input: str) -> AgentDecision:
        """Make a decision based on context and user input."""
        
        # Check for onboarding
        if context.user_profile and not context.user_profile.onboarding_completed:
            return self._decide_onboarding(context, user_input)
        
        # Check for tool use intent
        tool_decision = self._check_tool_intent(user_input, context)
        if tool_decision:
            return tool_decision
        
        # Check for memory storage intent
        memory_decision = self._check_memory_intent(user_input, context)
        if memory_decision:
            return memory_decision
        
        # Check for proactive suggestion opportunity
        if self._should_suggest(context, user_input):
            return self._generate_suggestion(context)
        
        # Check if we should ask follow-up
        if self._should_ask_followup(user_input, context):
            return self._generate_followup(context)
        
        # Default: just answer
        return AgentDecision(
            action_type=ActionType.ANSWER,
            response="",  # Will be filled by LLM
            reasoning="Default conversational response"
        )
    
    def _decide_onboarding(self, context: AgentContext, user_input: str) -> AgentDecision:
        """Handle onboarding flow decisions."""
        profile = context.user_profile
        
        if not profile.name:
            return AgentDecision(
                action_type=ActionType.ONBOARDING,
                response="",
                reasoning="Need user's name",
                followup_question="Hey! Nenu Ashu 😊 Me peru enti? Meeku em nick name istam?"
            )
        
        if not profile.nickname:
            return AgentDecision(
                action_type=ActionType.ONBOARDING,
                response="",
                reasoning="Need nickname",
                followup_question=f"Nice {profile.name}! Meeku em nick name istam? Naku 'Ashu' chaala ishtam 😊"
            )
        
        if not profile.interests:
            return AgentDecision(
                action_type=ActionType.ONBOARDING,
                response="",
                reasoning="Need interests",
                followup_question=f"Sari {profile.nickname}! Me interests enti? Hobbies, passions, em chesthe santosham vastundi?"
            )
        
        # Complete onboarding
        return AgentDecision(
            action_type=ActionType.ONBOARDING,
            response="",
            reasoning="Complete onboarding",
            memory_updates=[{"type": "profile", "onboarding_completed": True}],
            followup_question=f"Perfect {profile.nickname}! Onboarding complete 🎉 Ippudu em cheyyam? Chat, goals, projects - em kavali?"
        )
    
    def _check_tool_intent(self, user_input: str, context: AgentContext) -> Optional[AgentDecision]:
        """Check if user wants to use a tool."""
        user_lower = user_input.lower()
        
        # Check for explicit tool keywords
        for action_type, keywords in self._decision_keywords.items():
            if action_type == ActionType.USE_TOOL:
                for keyword in keywords:
                    if keyword in user_lower:
                        # Try to match to specific tool
                        tool_name, tool_args = self._match_tool(user_input, context)
                        if tool_name:
                            return AgentDecision(
                                action_type=ActionType.USE_TOOL,
                                tool_name=tool_name,
                                tool_args=tool_args,
                                reasoning=f"Detected tool intent: {keyword}"
                            )
        return None
    
    def _match_tool(self, user_input: str, context: AgentContext) -> tuple:
        """Match user input to a specific tool."""
        user_lower = user_input.lower()
        available_tools = self.tool_system.get_available_tools()
        
        # Simple keyword matching for tools
        tool_keywords = {
            "create_note": ["note", "notes", "write down", "save note", "remember this"],
            "create_reminder": ["remind", "reminder", "timer", "alarm", "alert"],
            "read_file": ["read", "open file", "show file", "cat"],
            "write_file": ["write file", "create file", "save file"],
            "list_files": ["list files", "show files", "ls", "files in"],
            "search_files": ["find file", "search file", "where is"],
            "get_time": ["time", "what time", "current time"],
            "get_date": ["date", "today", "what day"],
        }
        
        for tool_name, keywords in tool_keywords.items():
            if any(kw in user_lower for kw in keywords):
                if tool_name in available_tools:
                    # Extract arguments (simplified)
                    args = self._extract_tool_args(tool_name, user_input)
                    return tool_name, args
        
        return None, {}
    
    def _extract_tool_args(self, tool_name: str, user_input: str) -> Dict[str, Any]:
        """Extract tool arguments from user input (simplified)."""
        # In production, use LLM for argument extraction
        args = {}
        
        if tool_name == "create_note":
            # Extract note content after keywords
            import re
            match = re.search(r'(note|write down|save note|remember this)[\s:]+(.+)', user_input, re.IGNORECASE)
            if match:
                args["content"] = match.group(2).strip()
            else:
                args["content"] = user_input
        
        elif tool_name == "create_reminder":
            # Extract time and message
            args["message"] = user_input
            args["minutes"] = 5  # default
        
        elif tool_name in ["read_file", "write_file"]:
            # Extract file path
            import re
            match = re.search(r'[\w/\-\.]+\.(txt|md|json|py|js|ts)', user_input)
            if match:
                args["path"] = match.group(0)
        
        return args
    
    def _check_memory_intent(self, user_input: str, context: AgentContext) -> Optional[AgentDecision]:
        """Check if user wants to store something in memory."""
        user_lower = user_input.lower()
        
        for keyword in self._decision_keywords[ActionType.REMEMBER]:
            if keyword in user_lower:
                # Extract what to remember
                import re
                match = re.search(r'(remember|note down|save this|keep in mind|yad rakho|save|store|memorize)[\s:]+(.+)', user_input, re.IGNORECASE)
                content = match.group(2).strip() if match else user_input
                
                return AgentDecision(
                    action_type=ActionType.REMEMBER,
                    response="",
                    memory_updates=[{
                        "type": "fact",
                        "category": "user_note",
                        "fact": content,
                        "source": "user"
                    }],
                    reasoning=f"User wants to remember: {content[:50]}..."
                )
        
        return None
    
    def _should_suggest(self, context: AgentContext, user_input: str) -> bool:
        """Check if we should make a proactive suggestion."""
        # Check user preferences
        if context.user_preferences and not context.user_preferences.proactive_suggestions:
            return False
        
        # Check for boredom/unproductivity signals
        user_lower = user_input.lower()
        boredom_signals = ["bore", "boring", "nothing to do", "free", "jobless", "time pass"]
        
        if any(signal in user_lower for signal in boredom_signals):
            return True
        
        # Check if user has active goals but hasn't mentioned them
        if context.relevant_goals and not any(
            goal.title.lower() in user_lower for goal in context.relevant_goals
        ):
            return True
        
        return False
    
    def _generate_suggestion(self, context: AgentContext) -> AgentDecision:
        """Generate a proactive suggestion."""
        suggestions = []
        
        # Suggest based on goals
        if context.relevant_goals:
            goal = context.relevant_goals[0]
            suggestions.append(f"Me goal '{goal.title}' vuntundi, ippudu ah related em cheyyachu?")
        
        # Suggest based on projects
        if context.relevant_projects:
            project = context.relevant_projects[0]
            suggestions.append(f"Project '{project.name}' lo progress cheyyam?")
        
        # General suggestions
        if not suggestions:
            suggestions = [
                "Quick walk theeskova? 🚶‍♀️",
                "Water tagili! 💧",
                "5 min meditation chesko 🧘‍♀️",
                "Phone side petti emaina productive cheyyi 📵",
            ]
        
        return AgentDecision(
            action_type=ActionType.SUGGEST,
            response="",
            suggestions=suggestions,
            reasoning="Proactive suggestion based on context"
        )
    
    def _should_ask_followup(self, user_input: str, context: AgentContext) -> bool:
        """Check if we should ask a follow-up question."""
        # If user asked a question, we should answer not ask back
        if "?" in user_input or any(q in user_input.lower() for q in ["what", "how", "why", "when", "where", "enti", "ela", "enduku"]):
            return False
        
        # If conversation is stale (short responses), ask follow-up
        if len(context.recent_messages) > 2:
            last_user_msgs = [m for m in context.recent_messages[-4:] if m.role == "user"]
            if last_user_msgs and all(len(m.content.split()) < 5 for m in last_user_msgs):
                return True
        
        return False
    
    def _generate_followup(self, context: AgentContext) -> AgentDecision:
        """Generate a follow-up question."""
        followups = [
            "Inka em undi? 🤔",
            "Enti vachindi? 😊",
            "Meeru ela feel avthunnav? 🤗",
            "Kavali ante help chesukuntane 💪",
            "Vistaram ga cheppava? 📝",
        ]
        
        import random
        return AgentDecision(
            action_type=ActionType.ASK_FOLLOWUP,
            response="",
            followup_question=random.choice(followups),
            reasoning="Encourage user to elaborate"
        )


def create_decision_engine(tool_system: 'ToolSystem') -> DecisionEngine:
    """Factory function to create decision engine."""
    return DecisionEngine(tool_system)