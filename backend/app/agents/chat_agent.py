from app.services.applications import load_application
import re
from uuid import uuid4
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
        product_details = ""
        try:
            product_info = self.master_agent.get_product_info()
            products = product_info.get("products", [])
            product_details = ""
            if products:
                p = products[0]
                product_details = (
                    f"Product: {p['name']}. "
                    f"Amount: {p['amount_range']}. "
                    f"Tenure: {p['tenure_range']}. "
                    f"Interest: {p['interest_rate']}. "
                    f"Processing fee: {p['processing_fee']}. "
                    f"Prepayment: {p['prepayment']}."
                )

            if history and len(history) > 2:
                history_text = self._format_history(history[-8:])
                system = (
                    CONTEXT_AWARE_PROMPT.format(history=history_text)
                    + f"\nAnswer the user's question about our loan products. {product_details}"
                )
            else:
                system = (
                    SYSTEM_PROMPT + f"\nAnswer the user's question about our loan products. {product_details}"
                )

            return self.llm_service.chat(
                system_prompt=system,
                user_message=message,
            )
        except Exception:
            return product_details or "Our personal loans offer up to 20 lakhs at 14% interest for 6-60 months."

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

        if stage == "AWAITING_SALARY_SLIP" and state.get("application_id"):
            record = load_application(state["application_id"])
            if record and record["decision"]["result"]["status"] != "HOLD":
                state["decision"] = record["decision"]
                state["stage"] = stage = "DONE"
                if record["decision"]["stage"] == "SANCTION":
                    state["agents_consulted"] = list(dict.fromkeys(state.get("agents_consulted", []) + ["SANCTION"]))

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
            entity_types=list(entities.raw_matches),
        )

        # Track which agents participated
        agents_consulted = state.get("agents_consulted", [])

        # =====================================================
        # GLOBAL INTENTS (handle regardless of stage)
        # =====================================================

        if message.strip().lower() in ("cancel", "stop", "no thanks", "cancel application") and stage != "DONE":
            from app.services.applications import cancel_pending
            if state.get("application_id"):
                cancel_pending(state["application_id"])
            state.clear()
            state["stage"] = "CANCELLED"
            return {"reply": "Your application is closed. You can start a new chat whenever you wish.", "state": state}
        if stage == "CANCELLED":
            return {"reply": "This application is closed. Select New Chat to start again.", "state": state}

        if stage == "COLLECT_PHONE" and intent != Intent.ASK_QUESTION:
            digits = re.sub(r"[\s()-]", "", message).removeprefix("+91")
            if not (digits.isdigit() and len(digits) == 10):
                return {"reply": "Please enter the ten-digit phone on your demo CRM profile.", "state": state}
            state.update(phone=digits, stage="COLLECT_ADDRESS")
            return {"reply": "What street address is registered on that profile?", "state": state}

        if stage == "COLLECT_ADDRESS" and intent != Intent.ASK_QUESTION:
            if not self.master_agent.kyc_agent.verify_contact(state["pan"], state["phone"], message):
                state.update(stage="COLLECT_PHONE")
                return {"reply": "Those details do not match the CRM. Let's try your registered phone again.", "state": state}
            state.update(address=message.strip(), stage="PROCESSING")
            return await self.handle_message("", state, history)

        if stage == "COLLECT_PAN" and not entities.pan and intent != Intent.ASK_QUESTION:
            if not message.strip() or intent == Intent.GREETING:
                context = state.get("campaign") or "personal loan"
                return {"reply": f"Welcome! What would you like to fund with your {context} offer, and how much do you need? You can also start with your demo PAN.", "state": state}
            # A monthly-payment target is a separate monetary field from principal.
            budget = re.search(r"(?:emi|monthly payment|monthly instalment)\s*(?:under|below|of|around|up to)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(k)?\b", message, re.I)
            if budget:
                state["target_emi"] = float(budget[1].replace(",", "")) * (1000 if budget[2] else 1)
                entities = self.entity_extractor.extract(message[:budget.start()] + message[budget.end():])
            state["purpose"] = message[:200]
            if entities.amount and self.master_agent.validate_loan_params(entities.amount, 24)["status"] == "VALID":
                state["requested_amount"] = entities.amount
            if entities.tenure_months and 6 <= entities.tenure_months <= 60:
                state["requested_tenure"] = entities.tenure_months
            return {"reply": "I can compare repayment options for you. What is your demo PAN?", "state": state}

        if stage in ("HUMAN_REVIEW", "COLLECT_TENURE") and entities.tenure_months and "what if" in message.lower():
            return {"reply": self._quote(state["loan_amount"], entities.tenure_months) +
                    " To select it, say 'change to that tenure' with the number of months.", "state": state}

        if intent == Intent.FRUSTRATED:
            base = (
                "I understand this might be frustrating. "
                "I'm here to help you get your loan processed as quickly as possible. "
                "Let's continue where we left off."
            )
            return {"reply": self._llm_rephrase(base, history), "state": state}

        if intent == Intent.ASK_QUESTION:
            if "SALES" not in agents_consulted:
                agents_consulted.append("SALES")
                state["agents_consulted"] = agents_consulted
            reply = self._answer_question(message, history)
            prompts = {"COLLECT_INCOME": "What is your monthly income?", "COLLECT_TENURE": "Which tenure would you like?",
                       "COLLECT_PHONE": "What phone is registered on the profile?", "COLLECT_ADDRESS": "What is the registered address?",
                       "HUMAN_REVIEW": "Would you like to confirm the terms or change them?"}
            return {"reply": reply + " " + prompts.get(stage, ""), "state": state}

        if stage == "AWAITING_SALARY_SLIP" and intent != Intent.MODIFY:
            decision = state["decision"]
            return {"reply": decision["result"]["reason"], "state": state, "decision": decision}

        if intent == Intent.OUT_OF_SCOPE and not entities.raw_matches and message.strip():
            base = (
                "I can only help with personal loan applications. "
                "Would you like to apply for a loan? Please share your PAN card number to begin."
            )
            return {"reply": self._llm_rephrase(base, history), "state": state}

        if intent == Intent.MODIFY and stage != "DONE":
            state.pop("submission_key", None)
            if stage == "AWAITING_SALARY_SLIP":
                from app.services.applications import cancel_pending
                if old_id := state.pop("application_id", None):
                    cancel_pending(old_id)
                state.pop("decision", None)
                state.pop("human_confirmed", None)
                state["stage"] = "HUMAN_REVIEW"
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
                    f"Tenure: {state.get('tenure_months', 24)} months\n"
                    f"Interest Rate: 14%\n"
                    f"EMI: ₹{result.get('approved_emi'):,}\n\n"
                    f"Agents involved: {', '.join(state.get('agents_consulted', []))}\n\n"
                    f"You can download your sanction letter below."
                )
                return {
                    "reply": reply,
                    "state": state,
                    "decision": decision,
                    "sanction_letter_url": result["document"]["download_url"] if result.get("document") else f"/static/outputs/sanction_{sanction_id}.txt",
                }

            reply = (
                f"Your loan could not be approved.\n\n"
                f"Reason: {result.get('reason', 'Not eligible as per policy.')}\n"
                f"Stage: {decision.get('stage', 'Unknown')}\n"
                f"Agents involved: {', '.join(state.get('agents_consulted', []))}"
            )
            return {"reply": reply, "state": state, "decision": decision}

        # =====================================================
        # STAGE 1: COLLECT PAN — KYC Agent validates format
        # =====================================================
        if stage == "COLLECT_PAN":
            pan = entities.pan
            if pan:
                # KYC Agent validates PAN format in real-time
                pan_check = self.master_agent.validate_pan(pan)
                if pan_check["status"] == "INVALID":
                    reply = f"⚠️ {pan_check['reason']}"
                    return {"reply": reply, "state": state}

                state["pan"] = pan_check["pan"]
                state["stage"] = "COLLECT_INCOME"
                if "KYC" not in agents_consulted:
                    agents_consulted.append("KYC")
                state["agents_consulted"] = agents_consulted
                base = "Thanks. What is your monthly income?"
            else:
                base = "Please provide your PAN card number. It should be in the format ABCDE1234F."

            return {"reply": self._llm_rephrase(base, history), "state": state}

        # =====================================================
        # STAGE 2: COLLECT INCOME — Sales Agent context
        # =====================================================
        if stage == "COLLECT_INCOME":
            income = entities.income or entities.amount
            if income:
                state["monthly_income"] = income
                if state.get("requested_amount"):
                    state["stage"] = "COLLECT_LOAN"
                    return await self.handle_message(str(state.pop("requested_amount")), state, history)
                state["stage"] = "COLLECT_LOAN"
                if "SALES" not in agents_consulted:
                    agents_consulted.append("SALES")
                state["agents_consulted"] = agents_consulted
                reply = f"Got it, monthly income is ₹{income:,.0f}. How much loan amount are you looking for?"
            else:
                reply = self._llm_rephrase(
                    "I could not read your income. Please enter it as a number, for example 50000 or 5 lakhs.",
                    history,
                )

            return {"reply": reply, "state": state}

        # =====================================================
        # STAGE 3: COLLECT LOAN AMOUNT — Sales Agent validates
        # =====================================================
        if stage == "COLLECT_LOAN":
            loan = entities.amount or entities.income
            if loan:
                # Sales Agent validates loan parameters early
                param_check = self.master_agent.validate_loan_params(loan, 24)
                if param_check["status"] == "INVALID":
                    reasons = "; ".join(param_check["reasons"])
                    reply = f"⚠️ {reasons}. Please enter a valid loan amount."
                    return {"reply": reply, "state": state}

                state["loan_amount"] = loan
                state["stage"] = "COLLECT_TENURE"
                if "SALES" not in agents_consulted:
                    agents_consulted.append("SALES")
                state["agents_consulted"] = agents_consulted
                if state.get("requested_tenure"):
                    return await self.handle_message(f"{state.pop('requested_tenure')} months", state, history)
                target = state.get("target_emi")
                recommendation = ""
                if target:
                    affordable = next((n for n in range(6, 61)
                                       if self.master_agent.credit_agent.calculate_emi(loan, 14, n) <= target), None)
                    recommendation = ("\nShortest option within your monthly target: " + self._quote(loan, affordable)
                                      if affordable else "\nEven 60 months exceeds your target. You can reduce the amount.")
                reply = (self._quote(loan, 24) + "\n" + self._quote(loan, 36) + recommendation +
                         "\nWhich tenure works for you? You can choose 6 to 60 months.")
            else:
                reply = self._llm_rephrase(
                    "Please tell me the loan amount you need, for example 3 lakhs or 300000.",
                    history,
                )

            return {"reply": reply, "state": state}

        # =====================================================
        # STAGE 4: COLLECT TENURE — Sales Agent validates
        # =====================================================
        if stage == "COLLECT_TENURE":
            tenure = entities.tenure_months
            if tenure:
                # Sales Agent validates tenure
                param_check = self.master_agent.validate_loan_params(
                    state.get("loan_amount", 100000), tenure
                )
                if param_check["status"] == "INVALID":
                    reasons = "; ".join(param_check["reasons"])
                    reply = f"⚠️ {reasons}. Please enter a valid tenure."
                    return {"reply": reply, "state": state}

                state["tenure_months"] = tenure
                state["stage"] = "HUMAN_REVIEW"
            else:
                plain_num = entities.amount or entities.income
                if plain_num and 6 <= plain_num <= 60:
                    state["tenure_months"] = int(plain_num)
                    state["stage"] = "HUMAN_REVIEW"
                else:
                    base = "Please specify the loan tenure — for example '24 months' or '2 years'. We offer 6 to 60 months."
                    return {"reply": self._llm_rephrase(base, history), "state": state}

            if "SALES" not in agents_consulted:
                agents_consulted.append("SALES")
            state["agents_consulted"] = agents_consulted
            return self._show_review_summary(state, history)

        # =====================================================
        # STAGE 5: HUMAN-IN-THE-LOOP REVIEW
        # =====================================================
        if stage == "HUMAN_REVIEW":
            if intent == Intent.CONFIRM or entities.confirmation is True:
                state["stage"] = "PROCESSING"
                state["human_confirmed"] = True
                if not state.get("phone") or not state.get("address"):
                    state["stage"] = "COLLECT_PHONE"
                    return {"reply": "To verify your identity, what phone is registered on your demo CRM profile?", "state": state}
                stage = "PROCESSING"
            elif intent == Intent.DENY or entities.confirmation is False:
                state.pop("human_confirmed", None)
                base = "No problem. What would you like to change — PAN, income, loan amount, or tenure?"
                return {"reply": self._llm_rephrase(base, history), "state": state}
            elif intent == Intent.MODIFY:
                return self._handle_modify(message, state, entities, history)
            else:
                return self._show_review_summary(state, history)

        # =====================================================
        # STAGE 6: PROCESSING — Agents collaborate sequentially
        # =====================================================
        if stage == "PROCESSING":
            if not state.get("human_confirmed"):
                state["stage"] = "HUMAN_REVIEW"
                return self._show_review_summary(state, history)

            try:
                decision = await self.master_agent.process_loan_application(
                    request_key=state.setdefault("submission_key", str(uuid4())),
                    phone=state.get("phone", ""), address=state.get("address", ""),
                    pan=state["pan"], loan_amount=state["loan_amount"],
                    monthly_income=state["monthly_income"], tenure_months=state["tenure_months"],
                )
                for worker in ("SALES", "KYC", "CREDIT", "SANCTION"):
                    if worker not in agents_consulted:
                        agents_consulted.append(worker)
                    if worker == decision["stage"]:
                        break
                state["application_id"] = decision["application_id"]
                state["decision"] = decision
                state["agents_consulted"] = agents_consulted
                if decision["result"].get("status") == "HOLD":
                    state["stage"] = "AWAITING_SALARY_SLIP"
                    return {"reply": decision["result"]["reason"], "state": state, "decision": decision}
                state["stage"] = "DONE"
            except Exception:
                state["stage"] = "HUMAN_REVIEW"
                state.pop("human_confirmed", None)
                return {"reply": "Processing was interrupted. Your terms are saved. Confirm again to retry.", "state": state}

            return await self.handle_message("", state, history)

        # =====================================================
        # FALLBACK
        # =====================================================
        base = "Let me know if there is anything else I can help you with."
        return {"reply": self._llm_rephrase(base, history), "state": state}

    # -----------------------------
    # Human-in-the-loop summary
    # -----------------------------
    def _quote(self, amount, months):
        if not 6 <= months <= 60:
            return "Available tenures are 6 to 60 months."
        emi = self.master_agent.credit_agent.calculate_emi(amount, 14, months)
        return f"{months} months at 14%: EMI ₹{emi:,.2f}, total instalments ₹{emi * months:,.2f} before fees."

    def _show_review_summary(self, state: Dict[str, Any], history: List[Dict]) -> Dict[str, Any]:
        pan = state.get("pan", "N/A")
        income = state.get("monthly_income", 0)
        loan = state.get("loan_amount", 0)
        tenure = state.get("tenure_months", 24)

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
            if state.get("profile"):
                return {"reply": "Your custom profile uses a generated demo PAN. Start a new chat to change profiles.", "state": state}
            for field in ("phone", "address", "application_id", "human_confirmed", "decision"):
                state.pop(field, None)
            pan_check = self.master_agent.validate_pan(entities.pan)
            if pan_check["status"] == "INVALID":
                return {"reply": f"⚠️ {pan_check['reason']}", "state": state}
            state["pan"] = pan_check["pan"]
            base = f"Updated your PAN to {pan_check['pan']}. "
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
            reply = f"Updated income to ₹{entities.income:,.0f}. How much loan amount are you looking for?"
            return {"reply": reply, "state": state}

        if entities.amount:
            param_check = self.master_agent.validate_loan_params(
                entities.amount, state.get("tenure_months", 24)
            )
            if param_check["status"] == "INVALID":
                reasons = "; ".join(param_check["reasons"])
                return {"reply": f"⚠️ {reasons}. Please enter a valid loan amount.", "state": state}
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
            param_check = self.master_agent.validate_loan_params(
                state.get("loan_amount", 100000), entities.tenure_months
            )
            if param_check["status"] == "INVALID":
                reasons = "; ".join(param_check["reasons"])
                return {"reply": f"⚠️ {reasons}. Please enter a valid tenure.", "state": state}
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
