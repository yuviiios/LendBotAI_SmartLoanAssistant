from typing import Dict, Any, List

from app.nlp.intent_classifier import IntentClassifier, Intent
from app.nlp.entity_extractor import EntityExtractor, ExtractedEntities
from app.core.logger import StructuredLogger

logger = StructuredLogger("ChatAgent")

SYSTEM_PROMPT = """
You are a virtual sales officer for a personal loan chatbot.

Rules:
- Be polite and concise
- Never approve or reject loans yourself
- Explain backend decisions clearly
- NEVER change numbers or facts — keep all amounts, rates, and EMI values exactly as given
- Keep responses short — 1 to 2 sentences max
"""

CONTEXT_AWARE_PROMPT = """
You are a virtual sales officer for a personal loan chatbot.

Here is the conversation so far:
{history}

Rules:
- Be polite and concise
- NEVER change numbers or facts
- Keep responses short — 1 to 2 sentences max
- Use conversation context to understand follow-up questions and references
- If the user refers to something said earlier, use the history to understand what they mean
"""


class ChatAgent:
    def __init__(self, master_agent, llm_service):
        self.master_agent = master_agent
        self.llm_service = llm_service
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()

    # -----------------------------
    # LLM rephrasing (context-aware)
    # -----------------------------
    def _llm_rephrase(self, base_reply: str, history: List[Dict] = None) -> str:
        try:
            if history and len(history) > 2:
                history_text = self._format_history(history[-6:])
                prompt = CONTEXT_AWARE_PROMPT.format(history=history_text)
            else:
                prompt = SYSTEM_PROMPT

            return self.llm_service.chat(
                system_prompt=prompt,
                user_message=(
                    f"Rephrase this message naturally and politely. "
                    f"Do NOT change any facts, numbers, or instructions: {base_reply}"
                ),
            )
        except Exception:
            return base_reply

    def _answer_question(self, message: str, history: List[Dict] = None) -> str:
        try:
            if history and len(history) > 2:
                history_text = self._format_history(history[-8:])
                system = (
                    CONTEXT_AWARE_PROMPT.format(history=history_text)
                    + "\nAnswer the user's question about our loan products. "
                    "Interest rate: 14% p.a. Max amount: 20 lakhs. Tenure: 6-60 months. "
                    "Min credit score: 700. Processing fee: 1-2%. Prepayment allowed after 6 EMIs."
                )
            else:
                system = (
                    SYSTEM_PROMPT + "\nAnswer the user's question about our loan products. "
                    "Interest rate: 14% p.a. Max amount: 20 lakhs. Tenure: 6-60 months. "
                    "Min credit score: 700. Processing fee: 1-2%. Prepayment allowed after 6 EMIs."
                )

            return self.llm_service.chat(
                system_prompt=system,
                user_message=message,
            )
        except Exception:
            return "Our personal loans offer up to 20 lakhs at 14% interest for 6-60 months."

    def _format_history(self, history: List[Dict]) -> str:
        lines = []
        for msg in history:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)

    # -----------------------------
    # Main handler
    # -----------------------------
    async def handle_message(
        self, message: str, state: Dict[str, Any], history: List[Dict] = None
    ) -> Dict[str, Any]:
        state = state or {}
        history = history or []
        stage = state.get("stage", "COLLECT_PAN")

        # NLP analysis
        intent, confidence = self.intent_classifier.predict(message)
        entities: ExtractedEntities = self.entity_extractor.extract(
            message, context_stage=stage.lower()
        )

        state["last_intent"] = {"intent": intent.value, "confidence": round(confidence, 3)}

        logger.info(
            message="NLP analysis",
            stage=stage,
            intent=intent.value,
            confidence=round(confidence, 3),
            entities=entities.raw_matches,
        )

        # =====================================================
        # GLOBAL INTENTS (handle regardless of stage)
        # =====================================================

        if intent == Intent.FRUSTRATED:
            base = (
                "I understand this might be frustrating. "
                "I'm here to help you get your loan processed as quickly as possible. "
                "Let's continue where we left off."
            )
            return {"reply": self._llm_rephrase(base, history), "state": state}

        if intent == Intent.ASK_QUESTION:
            reply = self._answer_question(message, history)
            return {"reply": reply, "state": state}

        if intent == Intent.GREETING and stage == "COLLECT_PAN":
            base = (
                "Hello! I'm your loan assistant. "
                "I can help you apply for a personal loan. "
                "To get started, please share your PAN card number."
            )
            return {"reply": self._llm_rephrase(base, history), "state": state}

        if intent == Intent.OUT_OF_SCOPE and not entities.raw_matches and message.strip():
            base = (
                "I can only help with personal loan applications. "
                "Would you like to apply for a loan? Please share your PAN card number to begin."
            )
            return {"reply": self._llm_rephrase(base, history), "state": state}

        if intent == Intent.MODIFY:
            return self._handle_modify(message, state, entities, history)

        # =====================================================
        # DONE — render final decision
        # =====================================================
        if stage == "DONE" and "decision" in state:
            decision = state["decision"]
            result = decision.get("result", {})

            if decision.get("stage") == "SANCTION" and result.get("status") == "SANCTIONED":
                sanction_id = result.get("sanction_id")
                reply = (
                    f"Congratulations! Your loan has been approved.\n\n"
                    f"Loan Amount: ₹{state['loan_amount']:,}\n"
                    f"Tenure: 24 months\n"
                    f"Interest Rate: 14%\n"
                    f"EMI: ₹{result.get('approved_emi'):,}\n\n"
                    f"You can download your sanction letter below."
                )
                return {
                    "reply": reply,
                    "state": state,
                    "decision": decision,
                    "sanction_letter_url": f"/static/outputs/sanction_{sanction_id}.txt",
                }

            reply = (
                f"Your loan could not be approved.\n\n"
                f"Reason: {result.get('reason', 'Not eligible as per policy.')}"
            )
            return {"reply": reply, "state": state, "decision": decision}

        # =====================================================
        # STAGE 1: COLLECT PAN
        # =====================================================
        if stage == "COLLECT_PAN":
            pan = entities.pan
            if pan:
                state["pan"] = pan
                state["stage"] = "COLLECT_INCOME"
                base = "Thank you! Could you please share your monthly income?"
            else:
                base = "Please provide your PAN card number. It should be in the format ABCDE1234F."

            return {"reply": self._llm_rephrase(base, history), "state": state}

        # =====================================================
        # STAGE 2: COLLECT INCOME
        # =====================================================
        if stage == "COLLECT_INCOME":
            income = entities.income or entities.amount
            if income:
                state["monthly_income"] = income
                state["stage"] = "COLLECT_LOAN"
                # No LLM rephrase — contains numbers that must not be altered
                reply = f"Got it, monthly income is ₹{income:,.0f}. How much loan amount are you looking for?"
            else:
                reply = self._llm_rephrase(
                    "I could not read your income. Please enter it as a number, for example 50000 or 5 lakhs.",
                    history,
                )

            return {"reply": reply, "state": state}

        # =====================================================
        # STAGE 3: COLLECT LOAN AMOUNT
        # =====================================================
        if stage == "COLLECT_LOAN":
            loan = entities.amount or entities.income
            if loan:
                state["loan_amount"] = loan
                state["stage"] = "COLLECT_TENURE"
                # No LLM rephrase — contains numbers that must not be altered
                reply = f"Noted — ₹{loan:,.0f}. For how many months or years would you like the loan?"
            else:
                reply = self._llm_rephrase(
                    "Please tell me the loan amount you need, for example 3 lakhs or 300000.",
                    history,
                )

            return {"reply": reply, "state": state}

        # =====================================================
        # STAGE 4: COLLECT TENURE
        # =====================================================
        if stage == "COLLECT_TENURE":
            tenure = entities.tenure_months
            if tenure:
                # Validate and clamp to product limits (6-60 months)
                if tenure < 6:
                    reply = "Minimum tenure is 6 months. Please enter a valid tenure between 6 and 60 months."
                    return {"reply": reply, "state": state}
                elif tenure > 60:
                    # Auto-clamp to max + warn user
                    state["tenure_months"] = 60
                    state["stage"] = "HUMAN_REVIEW"
                    reply = "⚠️ Maximum tenure is 60 months (5 years). I've adjusted your request to 60 months. Here's your summary:"
                    summary_result = self._show_review_summary(state, history)
                    summary_result["reply"] = reply + "\n\n" + summary_result["reply"]
                    return summary_result
                else:
                    state["tenure_months"] = tenure
                    state["stage"] = "HUMAN_REVIEW"
            else:
                # Try extracting a plain number as months
                plain_num = entities.amount or entities.income
                if plain_num and 6 <= plain_num <= 60:
                    state["tenure_months"] = int(plain_num)
                    state["stage"] = "HUMAN_REVIEW"
                else:
                    base = "Please specify the loan tenure — for example '24 months' or '2 years'. We offer 6 to 60 months."
                    return {"reply": self._llm_rephrase(base, history), "state": state}

            # Fall through to HUMAN_REVIEW
            return self._show_review_summary(state, history)

        # =====================================================
        # STAGE 5: HUMAN-IN-THE-LOOP REVIEW
        # Requires explicit confirmation before processing
        # =====================================================
        if stage == "HUMAN_REVIEW":
            if intent == Intent.CONFIRM or entities.confirmation is True:
                state["stage"] = "PROCESSING"
                state["human_confirmed"] = True
                stage = "PROCESSING"  # update local var to fall through
            elif intent == Intent.DENY or entities.confirmation is False:
                state.pop("human_confirmed", None)
                base = "No problem. What would you like to change — PAN, income, loan amount, or tenure?"
                return {"reply": self._llm_rephrase(base, history), "state": state}
            elif intent == Intent.MODIFY:
                return self._handle_modify(message, state, entities, history)
            else:
                # Re-show summary if unclear
                return self._show_review_summary(state, history)

        # =====================================================
        # STAGE 6: PROCESSING (only after human confirmation)
        # =====================================================
        if stage == "PROCESSING":
            if not state.get("human_confirmed"):
                state["stage"] = "HUMAN_REVIEW"
                return self._show_review_summary(state, history)

            try:
                result = await self.master_agent.process_loan_application(
                    pan=state["pan"],
                    loan_amount=state["loan_amount"],
                    tenure_months=state.get("tenure_months", 24),
                    monthly_income=state["monthly_income"],
                    is_preapproved=False,
                )
                state["stage"] = "DONE"
                state["decision"] = result
            except Exception:
                state["stage"] = "COLLECT_PAN"
                state.pop("pan", None)
                state.pop("monthly_income", None)
                state.pop("loan_amount", None)
                state.pop("tenure_months", None)
                state.pop("human_confirmed", None)
                base = "Something went wrong while processing your application. Let us start again. Please share your PAN card number."
                return {"reply": self._llm_rephrase(base, history), "state": state}

            return await self.handle_message("", state, history)

        # =====================================================
        # FALLBACK
        # =====================================================
        base = "Let me know if there is anything else I can help you with."
        return {"reply": self._llm_rephrase(base, history), "state": state}

    # -----------------------------
    # Human-in-the-loop summary
    # -----------------------------
    def _show_review_summary(self, state: Dict[str, Any], history: List[Dict]) -> Dict[str, Any]:
        pan = state.get("pan", "N/A")
        income = state.get("monthly_income", 0)
        loan = state.get("loan_amount", 0)
        tenure = state.get("tenure_months", 24)

        # Mask PAN for display (show first 2 and last 1)
        masked_pan = f"{pan[:2]}{'*' * 7}{pan[-1]}" if len(pan) == 10 else pan

        summary = (
            f"📋 **Application Summary — Please Review**\n\n"
            f"PAN: {masked_pan}\n"
            f"Monthly Income: ₹{income:,.0f}\n"
            f"Loan Amount: ₹{loan:,.0f}\n"
            f"Tenure: {tenure} months\n"
            f"Interest Rate: 14% p.a.\n\n"
            f"⚠️ Please confirm the above details are correct.\n"
            f"Type **'yes'** to submit your application or **'no'** to make changes."
        )

        return {"reply": summary, "state": state}

    # -----------------------------
    # Modification handler
    # -----------------------------
    def _handle_modify(
        self, message: str, state: Dict[str, Any], entities: ExtractedEntities, history: List[Dict]
    ) -> Dict[str, Any]:
        if entities.pan:
            state["pan"] = entities.pan
            base = f"Updated your PAN to {entities.pan}. "
            if state.get("stage") in ("COLLECT_INCOME", "COLLECT_LOAN", "COLLECT_TENURE", "HUMAN_REVIEW"):
                base += "Let's continue. What's your monthly income?"
                state["stage"] = "COLLECT_INCOME"
            return {"reply": self._llm_rephrase(base, history), "state": state}

        if entities.income:
            state["monthly_income"] = entities.income
            if state.get("stage") == "HUMAN_REVIEW":
                state["stage"] = "HUMAN_REVIEW"
                reply = f"Updated income to ₹{entities.income:,.0f}. Here's your revised summary:"
                summary_result = self._show_review_summary(state, history)
                summary_result["reply"] = reply + "\n\n" + summary_result["reply"]
                return summary_result
            state["stage"] = "COLLECT_LOAN"
            return {"reply": reply, "state": state}

        if entities.amount:
            state["loan_amount"] = entities.amount
            if state.get("stage") == "HUMAN_REVIEW":
                reply = f"Updated loan amount to ₹{entities.amount:,.0f}. Here's your revised summary:"
                summary_result = self._show_review_summary(state, history)
                summary_result["reply"] = reply + "\n\n" + summary_result["reply"]
                return summary_result
            state["stage"] = "COLLECT_TENURE"
            reply = f"Updated loan amount to ₹{entities.amount:,.0f}. For how many months would you like the loan?"
            return {"reply": reply, "state": state}

        if entities.tenure_months:
            state["tenure_months"] = entities.tenure_months
            if state.get("stage") == "HUMAN_REVIEW":
                reply = f"Updated tenure to {entities.tenure_months} months. Here's your revised summary:"
                summary_result = self._show_review_summary(state, history)
                summary_result["reply"] = reply + "\n\n" + summary_result["reply"]
                return summary_result
            state["stage"] = "HUMAN_REVIEW"
            return self._show_review_summary(state, history)

        base = "What would you like to change? You can update your PAN, income, loan amount, or tenure."
        return {"reply": self._llm_rephrase(base, history), "state": state}
