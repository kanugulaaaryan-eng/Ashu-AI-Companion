"""
Ashu Agent - Main agent class orchestrating all components.
"""

import uuid
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

from memory.memory_interface import MemoryInterface
from memory.sqlite_memory import SQLiteMemory
from memory.models import UserProfile, UserPreferences
from personality.personality_engine import PersonalityEngine, PersonalityConfig, create_personality_engine
from personality.prompts import get_system_prompt
from brain.llm_interface import LLMInterface, ModelConfig, create_llm, MockLLM
from brain.context import ContextBuilder, AgentContext, ConversationMessage
from brain.decision import DecisionEngine, AgentDecision, ActionType
from tools.tool_system import ToolSystem
from tools.permissions import PermissionManager
from tools.confirmations import ConfirmationManager, PendingAction
from memory.memory_commands import handle_memory_command, MemoryCommandResult
from security.privacy import sanitize_model_output, is_sensitive


@dataclass
class AgentResponse:
    """Complete response from Ashu agent."""
    text: str
    action_type: ActionType
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    followup_question: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    # v0.3: what Ashu is "saying while thinking", and what the chibi
    # renderer/appearance system should show alongside this reply.
    thinking_line: str = ""
    animation: str = ""
    animation_duration: float = 0.0
    hairstyle: str = ""
    outfit: Dict[str, str] = field(default_factory=dict)
    sleep_state: str = "awake"
    # v0.4: honest inference provenance + interaction state.
    origin: str = "none"           # local | cloud | fallback | mock | rule_based | none
    provider: str = ""
    is_local: bool = False
    used_cloud: bool = False
    model_notice: str = ""          # shown when not running a real local model
    waiting_for_user: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    tool_activity: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0


class AshuAgent:
    """Main Ashu AI companion agent."""
    
    def __init__(
        self,
        memory: Optional[MemoryInterface] = None,
        personality: Optional[PersonalityEngine] = None,
        llm: Optional[LLMInterface] = None,
        tool_system: Optional[ToolSystem] = None,
        decision_engine: Optional[DecisionEngine] = None,
        config: Optional[ModelConfig] = None
    ):
        # Initialize components
        self.memory = memory or SQLiteMemory()
        self.personality = personality or PersonalityEngine()
        self.llm = llm or self._create_default_llm(config)
        self.tool_system = tool_system or ToolSystem(self.memory)
        self.decision_engine = decision_engine or DecisionEngine(self.tool_system)
        self.context_builder = ContextBuilder(self.memory, self.personality)
        self.permission_manager = PermissionManager()
        self._pending_wipe = False

        # v0.4: confirmation queue for risky tool actions + in-memory
        # tool-activity feed (also persisted to the activity log).
        self.confirmations = ConfirmationManager(require_confirmation=True)
        self.tool_activity: List[Dict[str, Any]] = []
        self._last_user_input = ""
        self._last_check_in_topic = ""

        # Session state
        self.session_id = str(uuid.uuid4())[:8]
        self.is_onboarding = False
        self._check_onboarding_status()
    
    def _create_default_llm(self, config: Optional[ModelConfig]) -> LLMInterface:
        """Create the default inference router.

        v0.4 routes through `InferenceRouter` so the agent always reports
        truthfully whether a real local model, cloud fallback, or the
        explicitly-labelled offline fallback produced the text.
        """
        from brain.inference import build_inference_router, CloudConfig
        prefs = self.memory.get_user_preferences()
        cloud = CloudConfig(
            enabled=bool(getattr(prefs, "cloud_fallback_enabled", False)),
        ) if prefs else None
        if config is not None and config.model_type == "mock":
            return build_inference_router(allow_mock=True)
        return build_inference_router(
            model_path=config.model_path if config else "",
            model_type=config.model_type if config else "llama_cpp",
            model_config=config, cloud=cloud,
        )
    
    def _check_onboarding_status(self) -> None:
        """Check if onboarding is needed."""
        profile = self.memory.get_user_profile()
        self.is_onboarding = profile is None or not profile.onboarding_completed
    
    async def process_message(self, user_input: str) -> AgentResponse:
        """Process user message and generate response."""
        self._last_user_input = user_input

        # v0.4: conversational memory commands take priority over generation
        # so "what do you remember" / "forget that" / "delete everything"
        # never depend on the model understanding them.
        wipe_confirmed = self._pending_wipe and user_input.strip().lower() in {
            "yes, delete everything", "yes delete everything", "confirm delete",
            "delete everything", "yes",
        }
        command = handle_memory_command(user_input, self.memory, confirmed=wipe_confirmed)
        if command.handled:
            self._pending_wipe = bool(command.requires_confirmation)
            try:
                self.memory.log_activity("memory", command.action, command.text[:200])
            except Exception:
                pass
            action = ActionType.REMEMBER if command.action in ("remember", "forget", "wipe") else ActionType.ANSWER
            response = AgentResponse(
                text=command.text, action_type=action,
                memory_updates=([{"type": "fact", "fact": command.data.get("fact", "")}]
                                if command.action == "remember" else []),
            )
            if self._is_question(command.text):
                self.personality.mark_waiting(command.text)
                response.waiting_for_user = True
            response.session_id = self.session_id
            self._attach_expression(response, self.memory.get_user_preferences())
            self._finalize_provenance(response)
            return response

        # Update Ashu's relationship/mood state from every interaction.
        # v0.3: gradual 5-stage progression (personality/relationship.py)
        # instead of a hard 2-threshold jump, driven by familiarity/trust
        # that live on prefs but are never shown to the user as raw numbers.
        prefs = self.memory.get_user_preferences()
        if prefs:
            prefs.interaction_count += 1
            self.personality.apply_preferences(prefs)
            stage = self.personality.advance_relationship(
                positive=not self._looks_abusive(user_input),
                respectful=not self._looks_abusive(user_input),
            )
            prefs.relationship_stage = stage.value
            prefs.familiarity = self.personality.relationship_state.familiarity
            prefs.trust = self.personality.relationship_state.trust
            self.memory.save_user_preferences(prefs)
            self.personality.apply_preferences(prefs)

        # Add user message to context
        self.context_builder.add_message("user", user_input)
        
        # Build context
        context = self.context_builder.build_context(user_input)
        self.personality.infer_mood(user_input, prefs)
        
        # Make decision
        decision = self.decision_engine.decide(context, user_input)
        
        # Execute decision
        response = await self._execute_decision(decision, context, user_input)
        
        # Add assistant response to context
        self.context_builder.add_message(
            "assistant", 
            response.text,
            tool_calls=[{"name": decision.tool_name, "args": decision.tool_args}] if decision.tool_name else [],
            tool_results=response.tool_results
        )
        
        # Handle memory updates
        if decision.memory_updates:
            await self._apply_memory_updates(decision.memory_updates)
        
        # Remember useful preferences/facts automatically, while avoiding secrets.
        self._auto_capture_memory(user_input)
        
        # Periodically summarize conversation
        if len(self.context_builder.get_conversation_history()) % 20 == 0:
            await self._summarize_conversation()
        
        response.session_id = self.session_id
        self._attach_expression(response, prefs)

        # v0.4: if she asked something, remember that she is waiting.
        if response.followup_question or self._is_question(response.text):
            self.personality.mark_waiting(response.followup_question or response.text)
            response.waiting_for_user = True
        # Keep the last topic for proactive check-ins/follow-ups.
        if response.action_type == ActionType.ANSWER and response.text:
            topics = self.context_builder.extract_key_topics(self.context_builder.get_conversation_history(limit=6))
            if topics:
                self.personality.set_conversation_context(topics[0])
        # Persist the personality state sidecar after each turn.
        try:
            self.personality.persist_state()
        except Exception:
            pass
        self._finalize_provenance(response)
        return response

    async def process_message_multi(self, user_input: str) -> list:
        """Process user message and generate multiple responses for multi-message support."""
        self._last_user_input = user_input

        # Handle memory commands (same as single message)
        wipe_confirmed = self._pending_wipe and user_input.strip().lower() in {
            "yes, delete everything", "yes delete everything", "confirm delete",
            "delete everything", "yes",
        }
        command = handle_memory_command(user_input, self.memory, confirmed=wipe_confirmed)
        if command.handled:
            self._pending_wipe = bool(command.requires_confirmation)
            try:
                self.memory.log_activity("memory", command.action, command.text[:200])
            except Exception:
                pass
            action = ActionType.REMEMBER if command.action in ("remember", "forget", "wipe") else ActionType.ANSWER
            response = AgentResponse(
                text=command.text, action_type=action,
                memory_updates=([{"type": "fact", "fact": command.data.get("fact", "")}]
                                if command.action == "remember" else []),
            )
            if self._is_question(command.text):
                self.personality.mark_waiting(command.text)
                response.waiting_for_user = True
            response.session_id = self.session_id
            self._attach_expression(response, self.memory.get_user_preferences())
            self._finalize_provenance(response)
            return [response]

        # Update Ashu's relationship/mood state from every interaction.
        prefs = self.memory.get_user_preferences()
        if prefs:
            prefs.interaction_count += 1
            self.personality.apply_preferences(prefs)
            stage = self.personality.advance_relationship(
                positive=not self._looks_abusive(user_input),
                respectful=not self._looks_abusive(user_input),
            )
            prefs.relationship_stage = stage.value
            prefs.familiarity = self.personality.relationship_state.familiarity
            prefs.trust = self.personality.relationship_state.trust
            self.memory.save_user_preferences(prefs)
            self.personality.apply_preferences(prefs)

        # Add user message to context
        self.context_builder.add_message("user", user_input)
        
        # Build context
        context = self.context_builder.build_context(user_input)
        self.personality.infer_mood(user_input, prefs)
        
        # Make decision
        decision = self.decision_engine.decide(context, user_input)
        
        # Execute decision
        response = await self._execute_decision(decision, context, user_input)
        
        # Add assistant response to context
        self.context_builder.add_message(
            "assistant", 
            response.text,
            tool_calls=[{"name": decision.tool_name, "args": decision.tool_args}] if decision.tool_name else [],
            tool_results=response.tool_results
        )
        
        # Handle memory updates
        if decision.memory_updates:
            await self._apply_memory_updates(decision.memory_updates)
        
        # Remember useful preferences/facts automatically, while avoiding secrets.
        self._auto_capture_memory(user_input)
        
        # Periodically summarize conversation
        if len(self.context_builder.get_conversation_history()) % 20 == 0:
            await self._summarize_conversation()
        
        response.session_id = self.session_id
        self._attach_expression(response, prefs)
        
        # v0.4: if she asked something, remember that she is waiting.
        if response.followup_question or self._is_question(response.text):
            self.personality.mark_waiting(response.followup_question or response.text)
            response.waiting_for_user = True
        # Keep the last topic for proactive check-ins/follow-ups.
        if response.action_type == ActionType.ANSWER and response.text:
            topics = self.context_builder.extract_key_topics(self.context_builder.get_conversation_history(limit=6))
            if topics:
                self.personality.set_conversation_context(topics[0])
        # Persist the personality state sidecar after each turn.
        try:
            self.personality.persist_state()
        except Exception:
            pass
        self._finalize_provenance(response)
        
        # For multi-message, we split the response into multiple parts if it's long
        # or if it contains multiple distinct ideas
        responses = [response]
        
        # Split long responses into multiple messages
        if len(response.text) > 300:
            # Split by sentences
            import re
            sentences = re.split(r'(?<=[.!?])\s+', response.text)
            if len(sentences) > 2:
                chunks = []
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > 200:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                    current_chunk += sentence + " "
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                if len(chunks) > 1:
                    responses = []
                    for i, chunk in enumerate(chunks):
                        chunk_response = AgentResponse(
                            text=chunk,
                            action_type=ActionType.ANSWER,
                            origin=response.origin,
                            provider=response.provider,
                            is_local=response.is_local,
                            used_cloud=response.used_cloud,
                            model_notice=response.model_notice if i == 0 else "",
                            waiting_for_user=False,
                        )
                        self._attach_expression(chunk_response, prefs)
                        self._finalize_provenance(chunk_response)
                        responses.append(chunk_response)
        
        return responses

    def _is_question(self, text: str) -> bool:
        return bool(text) and "?" in text

    def _finalize_provenance(self, response: AgentResponse) -> None:
        """Never claim a model produced a response that it did not."""
        if response.origin not in ("none", ""):
            return
        # A canned/rule-based reply came from Ashu's own dialogue logic, not
        # from a language model at all.
        response.origin = "rule_based"
        response.provider = "ashu_rules"
        response.is_local = True
        response.model_notice = ""

    def _looks_abusive(self, user_input: str) -> bool:
        lowered = user_input.lower()
        return any(w in lowered for w in ["stupid ai", "shut up", "useless", "hate you", "idiot"])

    def _attach_expression(self, response: AgentResponse, prefs) -> None:
        """Fill in the v0.3 'how Ashu looks/acts right now' fields."""
        context_hint = None
        if response.action_type == ActionType.SUGGEST and self.personality.mood.value == "annoyed":
            context_hint = "suggestion_rejected"
        elif response.action_type == ActionType.REMEMBER:
            context_hint = "task_completed"

        decision = self.personality.get_animation(context_hint=context_hint)
        response.animation = decision.action
        response.animation_duration = decision.duration

        appearance = self.personality.get_appearance(prefs)
        response.hairstyle = appearance.hairstyle
        response.outfit = appearance.outfit.as_dict()
        response.sleep_state = self.personality.sleep_state(prefs).value
    
    async def _execute_decision(
        self, 
        decision: AgentDecision, 
        context: AgentContext, 
        user_input: str
    ) -> AgentResponse:
        """Execute the agent's decision."""
        
        if decision.action_type == ActionType.ANSWER:
            return await self._generate_answer(context, user_input)
        
        elif decision.action_type == ActionType.USE_TOOL:
            return await self._execute_tool(decision, context)
        
        elif decision.action_type == ActionType.REMEMBER:
            return await self._handle_remember(decision, context)
        
        elif decision.action_type == ActionType.SUGGEST:
            return await self._handle_suggest(decision, context)
        
        elif decision.action_type == ActionType.ASK_FOLLOWUP:
            return await self._handle_followup(decision, context)
        
        elif decision.action_type == ActionType.ONBOARDING:
            return await self._handle_onboarding(decision, context, user_input)
        
        elif decision.action_type == ActionType.SUMMARIZE:
            return await self._summarize_conversation()
        
        # Fallback
        return AgentResponse(
            text="Em ledu ra babu 😭",
            action_type=ActionType.ANSWER
        )
    
    async def _generate_answer(self, context: AgentContext, user_input: str) -> AgentResponse:
        """Generate conversational answer using LLM."""
        # Format prompt
        prompt = self.context_builder.format_context_for_llm(context)
        prompt = prompt.replace("{user_input}", user_input)
        
        # Generate response
        llm_response = await self.llm.generate(prompt)

        # v0.4: treat every model output as untrusted text. Strip anything
        # that impersonates a system turn or tries to trigger a tool before
        # it ever reaches the personality formatter or the UI.
        safe_text = sanitize_model_output(llm_response.text)

        # Apply personality formatting
        profile = context.user_profile
        prefs = context.user_preferences
        formatted_response = self.personality.format_response(safe_text, profile, prefs)

        # She can "think" before answering -- a short filler line the UI can
        # show briefly, followed (once she's decided) by an "alr" style
        # acknowledgement worked into longer/considered replies.
        import random
        thinking = self.personality.thinking_line() if random.random() < 0.3 else ""

        return AgentResponse(
            text=formatted_response,
            action_type=ActionType.ANSWER,
            thinking_line=thinking,
            **self._provenance_fields(llm_response),
        )

    def _provenance_fields(self, llm_response) -> Dict[str, Any]:
        """Extract honest model-provenance fields from any LLM response."""
        origin = getattr(llm_response, "origin", "local")
        provider = getattr(llm_response, "provider", "")
        is_local = bool(getattr(llm_response, "is_local", origin == "local"))
        used_cloud = bool(getattr(llm_response, "used_cloud", origin == "cloud"))
        notice = ""
        if origin == "fallback":
            notice = "No local model is installed — reply came from offline fallback mode."
        elif origin == "mock":
            notice = "Mock brain (development only) — not a real language model."
        elif origin == "cloud":
            notice = f"This reply was sent to a cloud provider ({provider or 'cloud'})."
        return {
            "origin": origin, "provider": provider, "is_local": is_local,
            "used_cloud": used_cloud, "model_notice": notice,
        }
    
    async def _execute_tool(self, decision: AgentDecision, context: AgentContext) -> AgentResponse:
        """Execute a tool, gated by permissions + user confirmation (v0.4)."""
        from tools.permissions import PermissionLevel

        # Hard deny only when the user explicitly revoked the tool.
        if self.permission_manager.get_permission(decision.tool_name) == PermissionLevel.NEVER:
            return AgentResponse(
                text=f"Aa tool ki permission ledu ra. Settings lo grant cheyyali. 🔐",
                action_type=ActionType.USE_TOOL,
            )

        # Destructive/irreversible actions must be confirmed first.
        dangerous = self.permission_manager.is_dangerous(decision.tool_name)
        if self.confirmations.needs_confirmation(decision.tool_name, dangerous):
            action = self.confirmations.request(decision.tool_name, decision.tool_args)
            self._log_tool(decision.tool_name, decision.tool_args, "pending-confirmation", confirmed=False)
            return AgentResponse(
                text=(f"Idi cheyyadaniki nee confirm kavali ra: **{action.description}**.\n"
                      f"Sare aithe 'confirm' cheppu, vaddu aithe 'cancel'."),
                action_type=ActionType.USE_TOOL,
                pending_action=action.as_dict(),
            )

        result = await self.tool_system.execute_tool(decision.tool_name, decision.tool_args)
        self._log_tool(decision.tool_name, decision.tool_args,
                       "success" if result.success else f"failed: {result.error}", confirmed=False)

        if result.success:
            prompt = self.context_builder.format_context_for_llm(context)
            prompt += (f"\n\nTool '{decision.tool_name}' executed successfully.\n"
                       f"Result: {result.output}\n\nAshu:")
            llm_response = await self.llm.generate(prompt)
            safe_text = sanitize_model_output(llm_response.text)
            formatted = self.personality.format_response(safe_text, context.user_profile, context.user_preferences)
            return AgentResponse(
                text=formatted,
                action_type=ActionType.USE_TOOL,
                tool_results=[{"tool": decision.tool_name, "result": result.output}],
                tool_activity=[{"tool": decision.tool_name, "ok": True}],
                **self._provenance_fields(llm_response),
            )
        return AgentResponse(
            text=f"Tool pani cheyyaledu: {result.error} 😅",
            action_type=ActionType.USE_TOOL,
            tool_results=[{"tool": decision.tool_name, "error": result.error}],
            tool_activity=[{"tool": decision.tool_name, "ok": False, "error": result.error}],
        )

    def _log_tool(self, name: str, args: Dict[str, Any], detail: str, confirmed: bool) -> None:
        entry = {"tool": name, "detail": detail, "confirmed": confirmed}
        self.tool_activity.append(entry)
        self.tool_activity = self.tool_activity[-50:]
        try:
            self.memory.log_activity("tool", name, detail, {"args": args}, confirmed=confirmed)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # v0.4 confirmation API (used by the Android bridge/UI)
    # ------------------------------------------------------------------
    async def confirm_action(self, action_id: str) -> AgentResponse:
        action = self.confirmations.get(action_id)
        if not action or action.status != "pending":
            return AgentResponse(text="Aa action ippudu pending lo ledu.", action_type=ActionType.USE_TOOL)
        pending = self.confirmations.confirm(action_id)
        result = await self.tool_system.execute_tool(pending.tool_name, pending.args)
        self._log_tool(pending.tool_name, pending.args,
                       "success" if result.success else f"failed: {result.error}", confirmed=True)
        self.confirmations.mark_executed(action_id)
        if result.success:
            return AgentResponse(
                text=f"Sare, chesesa: {pending.description} ✅",
                action_type=ActionType.USE_TOOL,
                tool_results=[{"tool": pending.tool_name, "result": result.output}],
                tool_activity=[{"tool": pending.tool_name, "ok": True}],
            )
        return AgentResponse(
            text=f"Cheyyadaniki try chesa kani fail ayindi: {result.error} 😅",
            action_type=ActionType.USE_TOOL,
            tool_activity=[{"tool": pending.tool_name, "ok": False, "error": result.error}],
        )

    def cancel_action(self, action_id: str) -> AgentResponse:
        action = self.confirmations.cancel(action_id)
        text = "Sare, cancel chesa. Em cheyyaledu." if action else "Aa action dorakaledu."
        return AgentResponse(text=text, action_type=ActionType.USE_TOOL)

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        return [a.as_dict() for a in self.confirmations.list_pending()]

    def get_tool_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            return [
                {"kind": e.kind, "name": e.name, "detail": e.detail,
                 "confirmed": e.confirmed, "created_at": e.created_at.isoformat()}
                for e in self.memory.get_activity_log(limit)
            ]
        except Exception:
            return list(self.tool_activity[-limit:])
    
    async def _handle_remember(self, decision: AgentDecision, context: AgentContext) -> AgentResponse:
        """Handle memory storage request."""
        for update in decision.memory_updates:
            if update["type"] == "fact":
                from memory.models import UsefulFact
                self.memory.save_fact(
                    UsefulFact(
                        category=update.get("category", "user_note"),
                        fact=update["fact"],
                        source=update.get("source", "user")
                    )
                )
        
        return AgentResponse(
            text=self.personality.memory_ack(),
            action_type=ActionType.REMEMBER,
            memory_updates=decision.memory_updates
        )
    
    async def _handle_suggest(self, decision: AgentDecision, context: AgentContext) -> AgentResponse:
        """Handle proactive suggestion."""
        suggestion = decision.suggestions[0] if decision.suggestions else "Em cheyyam? 🤔"
        if self.personality.should_tease(context.recent_messages[-1].content if context.recent_messages else ""):
            suggestion = self.personality.boredom_response()
        elif self.personality.should_be_playfully_jealous(context.recent_messages[-1].content if context.recent_messages else ""):
            suggestion = self.personality.generate_playful_jealousy()
        
        return AgentResponse(
            text=suggestion,
            action_type=ActionType.SUGGEST,
            suggestions=decision.suggestions
        )
    
    async def _handle_followup(self, decision: AgentDecision, context: AgentContext) -> AgentResponse:
        """Handle follow-up question."""
        return AgentResponse(
            text=decision.followup_question,
            action_type=ActionType.ASK_FOLLOWUP,
            followup_question=decision.followup_question
        )
    
    async def _handle_onboarding(self, decision: AgentDecision, context: AgentContext, user_input: str) -> AgentResponse:
        """Handle the conversational onboarding state machine."""
        profile = self.memory.get_user_profile()
        if not profile:
            return AgentResponse(text="Hmm profile load avvaledu 😭", action_type=ActionType.ONBOARDING)

        answer = user_input.strip()
        lower = answer.lower()
        greetings = {"hi", "hey", "hello", "start", "skip", "hii", "hey ashu"}
        # Only treat a reply as the user's *name* when it actually looks like a
        # name (1-3 words, no question). Anything else is re-prompted, so a
        # first message like "hey ashu em chestunav?" is never saved as a name.
        looks_like_name = (
            0 < len(answer.split()) <= 3
            and "?" not in answer
            and not any(w in lower for w in ("how", "what", "why", "em", "enti", "ela", "chestunav"))
        )
        if answer and lower not in greetings:
            if not profile.name and looks_like_name:
                self.memory.update_user_profile(name=answer.split()[0].strip(" ,.!?"))
            elif profile.name and not profile.nickname and looks_like_name:
                self.memory.update_user_profile(nickname=answer.strip().strip(" ,.!?"))
            elif profile.name and profile.nickname and not profile.interests:
                interests = [item.strip() for item in answer.split(",") if item.strip()]
                if interests:
                    self.memory.update_user_profile(interests=interests)

        profile = self.memory.get_user_profile()
        if not profile.name:
            next_prompt = "Hey! Nenu Ashu 😊 Me peru enti?"
        elif not profile.nickname:
            next_prompt = f"Nice {profile.name}! Ninnu em ani pilavali? 😊"
        elif not profile.interests:
            next_prompt = "Saree. Nee interests enti? Hobbies, projects, games, anything ra 😌"
        else:
            if not profile.onboarding_completed:
                self.memory.update_user_profile(onboarding_completed=True)
            next_prompt = f"Perfect {profile.nickname}! Setup done 🎉 Ippudu mana chat start cheddama?"
            self._check_onboarding_status()

        return AgentResponse(
            text=next_prompt,
            action_type=ActionType.ONBOARDING,
            followup_question=next_prompt
        )
    
    async def _summarize_conversation(self) -> AgentResponse:
        """Summarize recent conversation and store."""
        messages = self.context_builder.get_conversation_history(limit=20)
        if len(messages) < 5:
            return AgentResponse(text="", action_type=ActionType.SUMMARIZE)
        
        # Create summary prompt
        summary_prompt = self.context_builder.create_summary_prompt(messages)
        
        # Generate summary
        llm_response = await self.llm.generate(summary_prompt)
        summary_text = llm_response.text.strip()
        
        # Extract key topics
        key_topics = self.context_builder.extract_key_topics(messages)
        
        # Save summary
        from memory.models import ConversationSummary
        summary = ConversationSummary(
            session_id=self.session_id,
            summary=summary_text,
            key_topics=key_topics,
            message_count=len(messages),
            started_at=messages[0].timestamp,
            ended_at=datetime.now()
        )
        self.memory.save_conversation_summary(summary)
        
        return AgentResponse(
            text=f"Conversation summarized: {summary_text}",
            action_type=ActionType.SUMMARIZE
        )
    
    async def _apply_memory_updates(self, updates: List[Dict[str, Any]]) -> None:
        """Apply memory updates from decisions."""
        for update in updates:
            if update["type"] == "profile":
                self.memory.update_user_profile(**{k: v for k, v in update.items() if k != "type"})
            elif update["type"] == "preferences":
                self.memory.update_user_preferences(**{k: v for k, v in update.items() if k != "type"})
            elif update["type"] == "fact":
                from memory.models import UsefulFact
                self.memory.save_fact(
                    UsefulFact(
                        category=update.get("category", "general"),
                        fact=update["fact"],
                        source=update.get("source", "agent")
                    )
                )
            elif update["type"] == "goal":
                from memory.models import UserGoal, GoalStatus
                goal = UserGoal(
                    title=update.get("title", ""),
                    description=update.get("description", ""),
                    status=GoalStatus(update.get("status", "active")),
                    priority=update.get("priority", 1)
                )
                self.memory.save_goal(goal)
    
    def _auto_capture_memory(self, user_input: str) -> None:
        prefs = self.memory.get_user_preferences()
        if not prefs or not prefs.auto_memory:
            return
        import re
        text = user_input.strip()
        # v0.4: one shared sensitive-content detector (security/privacy.py).
        if is_sensitive(text):
            return
        patterns = [
            (r"\b(?:i like|i love|i enjoy|naaku istam)\s+(.+)", "preference", 0.8),
            (r"\b(?:i hate|i don't like|naaku nachadu)\s+(.+)", "dislike", 0.8),
            (r"\b(?:my goal is|my goal:)\s+(.+)", "goal", 0.9),
            (r"\b(?:i am working on|i'm working on|working on)\s+(.+)", "project", 0.85),
            (r"\b(?:my favou?rite\s+\w+\s+is)\s+(.+)", "preference", 0.9),
        ]
        existing = {f.fact.strip().lower() for f in self.memory.get_facts() if getattr(f, "fact", None)}
        from memory.models import UsefulFact
        for pattern, category, confidence in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            fact = match.group(1).strip(" .!?\n")
            # Simple importance score: longer, more specific statements are
            # treated as more confident/important than one-word blurts.
            importance = min(1.0, confidence + (0.05 if len(fact.split()) >= 3 else 0))
            if 3 <= len(fact) <= 180 and fact.lower() not in existing:
                self.memory.save_fact(UsefulFact(
                    category=category, fact=fact, source="auto", confidence=importance,
                    session_id=self.session_id, source_message=text[:200],
                    memory_type="auto",
                ))
                existing.add(fact.lower())
                if category in ("project", "goal"):
                    self._last_check_in_topic = fact

        # Relationship/person extraction, e.g. "Rahul is my college friend".
        person_match = re.search(
            r"\b([A-Z][a-zA-Z]{1,20}) is my (\w[\w\s]{2,30}?)(?:\.|,|$)", text
        )
        if person_match:
            name, relation = person_match.group(1), person_match.group(2).strip()
            existing_people = {p.name.strip().lower() for p in self.memory.get_important_people()}
            if name.lower() not in existing_people:
                from memory.models import ImportantPerson
                self.memory.save_important_person(ImportantPerson(name=name, relationship=relation))

    def get_memory(self) -> MemoryInterface:
        """Get memory interface."""
        return self.memory
    
    def get_personality(self) -> PersonalityEngine:
        """Get personality engine."""
        return self.personality
    
    def get_tools(self) -> ToolSystem:
        """Get tool system."""
        return self.tool_system

    # ------------------------------------------------------------------
    # v0.4 public API used by the bridge / Android client
    # ------------------------------------------------------------------
    def get_personality_state(self) -> Dict[str, Any]:
        state = self.personality.get_state()
        return {
            "mood": state.mood,
            "energy": round(state.energy, 3),
            "familiarity": round(state.familiarity, 3),
            "trust": round(state.trust, 3),
            "boredom": round(state.boredom, 3),
            "relationship_stage": state.relationship_stage,
            "waiting_for_user": state.waiting_for_user,
            "conversation_context": state.conversation_context,
            "last_interaction_at": state.last_interaction_at,
        }

    def memory_snapshot(self, query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        facts = self.memory.search_all(query, limit=limit) if query else self.memory.get_all_memories(limit=limit)
        return [{
            "id": f.id, "category": f.category, "fact": f.fact,
            "source": f.source, "confidence": f.confidence,
            "memory_type": getattr(f, "memory_type", "auto"),
            "pinned": getattr(f, "pinned", False),
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat(),
        } for f in facts]

    def export_data(self) -> Dict[str, Any]:
        from security.privacy import DataExporter
        return DataExporter(self.memory).snapshot()

    def wipe_data(self) -> Dict[str, Any]:
        removed = self.memory.delete_all_memories()
        self.memory.wipe_all()
        return {"ok": True, "removed": removed}

    def handle_presence(self, *, idle_seconds: float, app_resumed: bool = False) -> Optional[Dict[str, Any]]:
        """App-lifecycle hook: lets Ashu greet a returning user.

        `idle_seconds` is the permitted signal (time since last interaction).
        Returns a proactive message dict or None.
        """
        prefs = self.memory.get_user_preferences()
        if prefs and not prefs.proactive_enabled:
            return None
        message = self.personality.maybe_proactive(
            idle_seconds=idle_seconds,
            check_in_topic=self._last_check_in_topic,
            conversation_context=self.personality.get_state().conversation_context,
        )
        if not message:
            return None
        try:
            self.memory.log_activity("proactive", message.kind, message.text[:200])
        except Exception:
            pass
        return {"text": message.text, "kind": message.kind, "animation": message.animation}
    
    def reset_session(self) -> None:
        """Reset conversation session."""
        self.context_builder.clear_history()
        self.session_id = str(uuid.uuid4())[:8]
    
    async def stream_response(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream response tokens (for real-time UI).

        v0.4 streams directly from the inference router when the active
        provider supports it (llama-cpp-python / cloud SSE). Otherwise it
        falls back to chunking the full reply so the contract never breaks.
        """
        self._last_user_input = user_input
        prefs = self.memory.get_user_preferences()
        if prefs:
            self.personality.apply_preferences(prefs)
        self.context_builder.add_message("user", user_input)
        context = self.context_builder.build_context(user_input)
        prompt = self.context_builder.format_context_for_llm(context)
        prompt = prompt.replace("{user_input}", user_input)
        try:
            async for chunk in self.llm.stream_generate(prompt):
                yield chunk
        except Exception:
            response = await self._generate_answer(context, user_input)
            for word in sanitize_model_output(response.text).split():
                yield word + " "
        self.context_builder.add_message("assistant", "")


def create_agent(
    db_path: str = "ashu_memory.db",
    model_config: Optional[ModelConfig] = None,
    use_mock_llm: bool = False,
    state_path: Optional[str] = None,
    cloud: Optional["CloudConfig"] = None,
) -> AshuAgent:
    """Factory function to create a fully configured Ashu agent.

    v0.4 defaults to the real `InferenceRouter` (local model -> cloud -> a
    labelled offline fallback). Pass `use_mock_llm=True` only for tests/demos.
    """
    from personality.state import JSONStateStore
    from brain.inference import build_inference_router, CloudConfig

    memory = SQLiteMemory(db_path)
    profile = memory.get_user_profile()
    prefs = memory.get_user_preferences()

    # Personality with a persistent state sidecar so the character survives
    # an app restart.
    sidecar = state_path or (db_path + ".state.json" if not db_path.endswith(".db")
                             else db_path[:-3] + ".state.json")
    personality = PersonalityEngine(state_store=JSONStateStore(sidecar))
    if prefs:
        personality.apply_preferences(prefs)

    if use_mock_llm:
        llm = build_inference_router(allow_mock=True)
    else:
        # An explicit cloud config (e.g. `serve.py --cloud`) wins; otherwise the
        # user's own "cloud fallback" preference decides.
        if cloud is None:
            cloud = CloudConfig(enabled=bool(getattr(prefs, "cloud_fallback_enabled", False))) if prefs else None
        llm = build_inference_router(
            model_path=model_config.model_path if model_config else "",
            model_type=model_config.model_type if model_config else "llama_cpp",
            model_config=model_config,
            cloud=cloud,
        )

    tool_system = ToolSystem(memory)
    agent = AshuAgent(
        memory=memory,
        personality=personality,
        llm=llm,
        tool_system=tool_system,
    )
    return agent