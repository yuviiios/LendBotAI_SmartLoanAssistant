from app.agents.sanction_agent import SanctionAgent


def test_sanction_auto_approved_loan():
    agent = SanctionAgent()

    credit_decision = {
        "status": "AUTO_APPROVE",
        "emi": 9500,
        "score": 780,
        "tenure": 24,
        "loan_amount": 100000,  # FIX: was missing — sanction letter does
                                # f"₹{loan_amount:,.2f}" which crashes if
                                # loan_amount is "N/A" (string, not float)
    }

    result = agent.sanction_loan(credit_decision)

    assert result["status"] == "SANCTIONED"
    assert "sanction_id" in result
    assert result["approved_emi"] == 9500


def test_sanction_conditional_approved_loan():
    agent = SanctionAgent()

    credit_decision = {
        "status": "CONDITIONAL_APPROVE",
        "emi": 10500,
        "score": 720,
        "tenure": 36,
        "loan_amount": 150000,  # FIX: same reason — needed for letter formatting
    }

    result = agent.sanction_loan(credit_decision)

    assert result["status"] == "SANCTIONED"
    assert result["terms"]["tenure_months"] == 36


def test_sanction_rejected_loan():
    agent = SanctionAgent()

    # No loan_amount needed here — rejected loans never reach
    # _generate_sanction_letter() so the format crash can't happen
    credit_decision = {
        "status": "REJECT",
        "reason": "Low credit score",
    }

    result = agent.sanction_loan(credit_decision)

    assert result["status"] == "NOT_SANCTIONED"
    assert result["credit_status"] == "REJECT"