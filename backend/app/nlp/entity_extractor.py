"""
Named Entity Recognition for financial/loan domain.

Extracts: PAN numbers, monetary amounts (with Indian notation),
tenure/duration, and phone numbers.

Uses regex patterns enhanced with contextual rules — more robust
than the bare regex in chat_agent.py because it handles:
  - Multiple entities in one message
  - Indian currency notation (lakhs, crores, L, Cr, ₹)
  - Relative modifications ("make it 5 lakhs instead")
  - Duration expressions ("2 years", "36 months")
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedEntities:
    pan: Optional[str] = None
    amount: Optional[float] = None
    income: Optional[float] = None
    tenure_months: Optional[int] = None
    phone: Optional[str] = None
    confirmation: Optional[bool] = None
    raw_matches: dict = field(default_factory=dict)


class EntityExtractor:
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")

    AMOUNT_PATTERNS = [
        (re.compile(r"(?:₹|rs\.?|inr)\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)\s*(?:crore|cr)\b", re.IGNORECASE), 1e7),
        (re.compile(r"(\d+(?:\.\d+)?)\s*(?:crore|cr)\b", re.IGNORECASE), 1e7),
        (re.compile(r"(?:₹|rs\.?|inr)\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b", re.IGNORECASE), 1e5),
        (re.compile(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b", re.IGNORECASE), 1e5),
        (re.compile(r"(?:₹|rs\.?|inr)\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)\s*(?:k)\b", re.IGNORECASE), 1e3),
        (re.compile(r"(\d+(?:\.\d+)?)\s*(?:k)\b", re.IGNORECASE), 1e3),
        (re.compile(r"(?:₹|rs\.?|inr)\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)", re.IGNORECASE), 1),
        (re.compile(r"\b(\d{4,10})\b"), 1),
    ]

    TENURE_PATTERNS = [
        (re.compile(r"(\d+)\s*(?:year|years|yr|yrs)\b", re.IGNORECASE), 12),
        (re.compile(r"(\d+)\s*(?:month|months|mo|mos)\b", re.IGNORECASE), 1),
    ]

    PHONE_PATTERN = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")

    CONFIRM_PATTERN = re.compile(
        r"\b(yes|yeah|yep|confirm|okay|ok|correct|proceed|sure|right|haan|ha)\b",
        re.IGNORECASE,
    )
    DENY_PATTERN = re.compile(
        r"\b(no|nope|nah|cancel|stop|wrong|incorrect|change|nahin)\b",
        re.IGNORECASE,
    )

    INCOME_CONTEXT = re.compile(
        r"(?:earn|income|salary|making|get paid|per month|monthly|pm)\b",
        re.IGNORECASE,
    )

    def extract(self, text: str, context_stage: str = "") -> ExtractedEntities:
        result = ExtractedEntities()
        clean_text = text.strip()

        # PAN
        pan_match = self.PAN_PATTERN.search(clean_text.upper())
        if pan_match:
            result.pan = pan_match.group()
            result.raw_matches["pan"] = pan_match.group()

        # Amount
        amount = self._extract_amount(clean_text)
        if amount is not None:
            if context_stage == "collect_income" or self.INCOME_CONTEXT.search(clean_text):
                result.income = amount
            else:
                result.amount = amount
            result.raw_matches["amount"] = amount

        # Tenure
        tenure = self._extract_tenure(clean_text)
        if tenure is not None:
            result.tenure_months = tenure
            result.raw_matches["tenure_months"] = tenure

        # Phone
        phone_match = self.PHONE_PATTERN.search(clean_text)
        if phone_match:
            result.phone = phone_match.group()
            result.raw_matches["phone"] = phone_match.group()

        # Confirmation / Denial
        if self.CONFIRM_PATTERN.search(clean_text):
            result.confirmation = True
        elif self.DENY_PATTERN.search(clean_text):
            result.confirmation = False

        return result

    def _extract_amount(self, text: str) -> Optional[float]:
        text_no_commas = text.replace(",", "")
        for pattern, multiplier in self.AMOUNT_PATTERNS:
            search_text = text if multiplier == 1 and "," in text else text_no_commas
            match = pattern.search(search_text if multiplier != 1 else text)
            if match:
                try:
                    raw_val = match.group(1).replace(",", "")
                    value = float(raw_val) * multiplier
                    return int(value) if value == int(value) else value
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_tenure(self, text: str) -> Optional[int]:
        for pattern, multiplier in self.TENURE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    return int(match.group(1)) * multiplier
                except (ValueError, IndexError):
                    continue
        return None
