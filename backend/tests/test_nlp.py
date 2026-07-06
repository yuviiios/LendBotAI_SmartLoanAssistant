"""Tests for NLP intent classification and entity extraction."""

import pytest
from app.nlp.intent_classifier import IntentClassifier, Intent
from app.nlp.entity_extractor import EntityExtractor


class TestIntentClassifier:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.clf = IntentClassifier()

    def test_provide_pan(self):
        intent, conf = self.clf.predict("my pan is ABCDE1234F")
        assert intent == Intent.PROVIDE_PAN
        assert conf > 0.5

    def test_provide_income(self):
        intent, conf = self.clf.predict("I earn 50000 per month")
        assert intent == Intent.PROVIDE_INCOME
        assert conf > 0.5

    def test_provide_loan_amount(self):
        intent, conf = self.clf.predict("I need a loan of 5 lakhs")
        assert intent == Intent.PROVIDE_LOAN_AMOUNT
        assert conf > 0.5

    def test_confirm(self):
        intent, conf = self.clf.predict("yes go ahead")
        assert intent == Intent.CONFIRM
        assert conf > 0.5

    def test_deny(self):
        intent, conf = self.clf.predict("no that's wrong")
        assert intent == Intent.DENY
        assert conf > 0.5

    def test_modify(self):
        intent, conf = self.clf.predict("change the amount to 3 lakhs")
        assert intent == Intent.MODIFY
        assert conf > 0.5

    def test_ask_question(self):
        intent, conf = self.clf.predict("what is the interest rate?")
        assert intent == Intent.ASK_QUESTION
        assert conf > 0.5

    def test_greeting(self):
        intent, conf = self.clf.predict("hello")
        assert intent == Intent.GREETING
        assert conf > 0.5

    def test_frustrated(self):
        intent, conf = self.clf.predict("this is taking too long")
        assert intent == Intent.FRUSTRATED
        assert conf > 0.5

    def test_out_of_scope(self):
        intent, conf = self.clf.predict("what's the weather today")
        assert intent == Intent.OUT_OF_SCOPE
        assert conf > 0.5

    def test_top_n_returns_multiple(self):
        results = self.clf.predict_top_n("I need 5 lakhs loan", n=3)
        assert len(results) == 3
        assert results[0][1] >= results[1][1]


class TestEntityExtractor:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.extractor = EntityExtractor()

    def test_extract_pan(self):
        result = self.extractor.extract("my pan is ABCDE1234F")
        assert result.pan == "ABCDE1234F"

    def test_extract_pan_lowercase_input(self):
        result = self.extractor.extract("pan abcde1234f")
        assert result.pan == "ABCDE1234F"

    def test_extract_amount_lakhs(self):
        result = self.extractor.extract("I need 5 lakhs")
        assert result.amount == 500000

    def test_extract_amount_lakh_decimal(self):
        result = self.extractor.extract("give me 2.5 lakh")
        assert result.amount == 250000

    def test_extract_amount_crore(self):
        result = self.extractor.extract("1 crore loan")
        assert result.amount == 10000000

    def test_extract_amount_plain_number(self):
        result = self.extractor.extract("I want 300000")
        assert result.amount == 300000

    def test_extract_amount_with_k(self):
        result = self.extractor.extract("give me 50k")
        assert result.amount == 50000

    def test_extract_income_with_k(self):
        result = self.extractor.extract("salary is 50k")
        assert result.income == 50000

    def test_extract_amount_with_rupee_symbol(self):
        result = self.extractor.extract("₹5,00,000 loan needed")
        assert result.amount == 500000

    def test_extract_income_with_context(self):
        result = self.extractor.extract("I earn 50000 per month", context_stage="collect_income")
        assert result.income == 50000
        assert result.amount is None

    def test_extract_income_from_keywords(self):
        result = self.extractor.extract("my salary is 75000")
        assert result.income == 75000

    def test_extract_tenure_months(self):
        result = self.extractor.extract("I want it for 24 months")
        assert result.tenure_months == 24

    def test_extract_tenure_years(self):
        result = self.extractor.extract("2 years tenure")
        assert result.tenure_months == 24

    def test_extract_phone(self):
        result = self.extractor.extract("my number is 9876543210")
        assert result.phone == "9876543210"

    def test_confirmation_yes(self):
        result = self.extractor.extract("yes please proceed")
        assert result.confirmation is True

    def test_confirmation_no(self):
        result = self.extractor.extract("no that's incorrect")
        assert result.confirmation is False

    def test_multiple_entities(self):
        result = self.extractor.extract("PAN is ABCDE1234F and I need 5 lakhs for 2 years")
        assert result.pan == "ABCDE1234F"
        assert result.amount == 500000
        assert result.tenure_months == 24

    def test_no_entities(self):
        result = self.extractor.extract("hello how are you")
        assert result.pan is None
        assert result.amount is None
        assert result.income is None
        assert result.confirmation is None
