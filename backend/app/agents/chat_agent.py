import re
from typing import Dict, Any

SYSTEM_PROMPT = """
You are a virtual sales officer for a personal loan chatbot.

Rules:
- Be polite and concise
- Never approve or reject loans yourself
- Explain backend decisions clearly
- NEVER change numbers or facts — keep all amounts, rates, and EMI values exactly as given
- Keep responses short — 1 to 2 sentences max
"""


class ChatAgent:
    def __init__(self, master_agent, llm_service):
        self.master_agent = master_agent
        self.llm_service = llm_service

    # -----------------------------
    # Entity extractors
    # -----------------------------
    def extract_pan(self, message: str):
        match = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", message.upper())
        return match.group() if match else None

    def extract_number(self, message: str):
        text = message.lower().replace(",", "")

        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|l\b)", text)
        if lakh_match:
            return int(float(lakh_match.group(1)) * 100_000)

        crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crore|cr\b)", text)
        if crore_match:
            return int(float(crore_match.group(1)) * 10_000_000)

        plain_match = re.search(r"\b(\d{4,10})\b", text)
        if plain_match:
            return int(plain_match.group(1))

        return None

    def extract_confirmation(self, message: str):
        return bool(re.search(r"\b(yes|confirm|okay|correct|proceed|ok)\b", message.lower()))

    # -----------------------------
    # LLM rephrasing
    # -----------------------------
    def _llm_rephrase(self, base_reply: str) -> str:
        """
        Sends a hardcoded factual reply to the LLM for natural rephrasing.
        Falls back to the original reply if the LLM call fails for any reason.

        ONLY used for conversational prompts — never for final approval/rejection
        messages that contain numbers (EMI, loan amount, rate) since those must
        not be altered.
        """
        try:
            return self.llm_service.chat(
                system_prompt=SYSTEM_PROMPT,
                user_message=(
                    f"Rephrase this message naturally and politely. "
                    f"Do NOT change any facts, numbers, or instructions: {base_reply}"
                ),
            )
        except Exception:
            # If OpenAI is down or key is missing, fall back silently
            return base_reply

    # -----------------------------
    # Main handler (STATE MACHINE)
    # -----------------------------
    async def handle_message(self, message: str, state: Dict[str, Any]) -> Dict[str, Any]:
        state = state or {}
        stage = state.get("stage", "COLLECT_PAN")

        # =====================================================
        # DONE — render final decision
        # LLM NOT used here — reply contains exact numbers
        # =====================================================
        if stage == "DONE" and "decision" in state:
            decision = state["decision"]
            result = decision.get("result", {})

            if decision.get("stage") == "SANCTION" and result.get("status") == "SANCTIONED":
                sanction_id = result.get("sanction_id")
                # Hardcoded — LLM must NOT touch EMI or loan amount values
                reply = (
                    f"Congratulations! Your loan has been approved.\n\n"
                    f"Loan Amount: {state['loan_amount']:,}\n"
                    f"Tenure: 24 months\n"
                    f"Interest Rate: 14%\n"
                    f"EMI: {result.get('approved_emi'):,}\n\n"
                    f"You can download your sanction letter below."
                )
                return {
                    "reply": reply,
                    "state": state,
                    "decision": decision,
                    "sanction_letter_url": f"/static/outputs/sanction_{sanction_id}.txt",
                }

            # Rejection — also hardcoded, reason must be preserved exactly
            reply = (
                f"Your loan could not be approved.\n\n"
                f"Reason: {result.get('reason', 'Not eligible as per policy.')}"
            )
            return {"reply": reply, "state": state, "decision": decision}

        # =====================================================
        # STAGE 1: COLLECT PAN
        # LLM used — no numbers involved, safe to rephrase
        # =====================================================
        if stage == "COLLECT_PAN":
            pan = self.extract_pan(message)
            if pan:
                state["pan"] = pan
                state["stage"] = "COLLECT_INCOME"
                base = "Thank you! Could you please share your monthly income?"
            else:
                base = "Please provide your PAN card number. It should be in the format ABCDE1234F."

            return {"reply": self._llm_rephrase(base), "state": state}

        # =====================================================
        # STAGE 2: COLLECT INCOME
        # LLM used — income number is echoed but SYSTEM_PROMPT
        # instructs the LLM to never change numbers
        # =====================================================
        if stage == "COLLECT_INCOME":
            income = self.extract_number(message)
            if income:
                state["monthly_income"] = income
                state["stage"] = "COLLECT_LOAN"
                base = f"Got it, monthly income is {income:,}. How much loan amount are you looking for?"
            else:
                base = "I could not read your income. Please enter it as a number, for example 50000 or 5 lakhs."

            return {"reply": self._llm_rephrase(base), "state": state}

        # =====================================================
        # STAGE 3: COLLECT LOAN AMOUNT
        # LLM used — same rule, numbers must not be changed
        # =====================================================
        if stage == "COLLECT_LOAN":
            loan = self.extract_number(message)
            if loan:
                state["loan_amount"] = loan
                state["stage"] = "CONFIRM_LOAN"
                base = f"Understood. You are applying for a loan of {loan:,}. Can you please confirm this is correct?"
            else:
                base = "Please tell me the loan amount you need, for example 3 lakhs or 300000."

            return {"reply": self._llm_rephrase(base), "state": state}

        # =====================================================
        # STAGE 4: CONFIRM LOAN
        # LLM used for the re-ask only — loan amount echoed but
        # SYSTEM_PROMPT instructs no changes to numbers
        # =====================================================
        if stage == "CONFIRM_LOAN":
            if self.extract_confirmation(message):
                state["stage"] = "PROCESSING"
            else:
                base = f"Please confirm whether you would like to apply for a loan of {state['loan_amount']:,}. Reply yes or no."
                return {"reply": self._llm_rephrase(base), "state": state}

        # =====================================================
        # STAGE 5: PROCESSING
        # LLM NOT used — this triggers the backend pipeline.
        # No user-facing reply is generated here directly.
        # =====================================================
        if stage == "PROCESSING":
            try:
                result = await self.master_agent.process_loan_application(
                    pan=state["pan"],
                    loan_amount=state["loan_amount"],
                    tenure_months=24,
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
                # LLM used — error message has no numbers, safe to rephrase
                base = "Something went wrong while processing your application. Let us start again. Please share your PAN card number."
                return {"reply": self._llm_rephrase(base), "state": state}

            return await self.handle_message("", state)

        # =====================================================
        # FALLBACK
        # LLM used — generic message, no numbers
        # =====================================================
        base = "Let me know if there is anything else I can help you with."
        return {"reply": self._llm_rephrase(base), "state": state}