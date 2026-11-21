from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.customer_directory import find_customer


class LoanState(TypedDict, total=False):
    application_id: str
    phone: str
    address: str
    pan: str
    loan_amount: float
    monthly_income: float
    tenure_months: int
    verified_salary: float
    previous_credit: dict
    stage: str
    result: dict


def compile_workflow(master):
    def sales(s):
        return {"stage": "SALES", "result": master.consult_sales(
            s["loan_amount"], s["tenure_months"], s["monthly_income"])}

    def kyc(s):
        result = master.consult_kyc(s["pan"])
        if result["status"] == "VERIFIED" and not master.kyc_agent.verify_contact(
                s["pan"], s.get("phone", ""), s.get("address", "")):
            result = {"status": "FAILED", "reason": "Phone or address does not match the demo CRM."}
        return {"stage": "KYC", "result": result}

    async def credit(s):
        if "previous_credit" in s:
            quote = s["previous_credit"]
            decision = master.credit_agent.evaluate_eligibility(
                score=quote["score"], loan_amount=quote["loan_amount"], tenure=quote["tenure"],
                preapproved_limit=quote["preapproved_limit"], annual_rate=quote["annual_rate"],
                verified_monthly_salary=s["verified_salary"])
        else:
            decision = await master.consult_credit(s["pan"], s["loan_amount"], s["tenure_months"])
        return {"stage": "CREDIT", "result": decision}

    def sanction(s):
        customer = find_customer(s["pan"])
        result = master.consult_sanction(dict(s["result"], application_id=s["application_id"],
                                             customer_name=customer.name))
        return {"stage": "SANCTION", "result": result}

    graph = StateGraph(LoanState)
    for name, worker in [("sales", sales), ("kyc", kyc), ("credit", credit), ("sanction", sanction)]:
        graph.add_node(name, worker)
    graph.add_conditional_edges(START, lambda s: "credit" if "previous_credit" in s else "sales")
    graph.add_conditional_edges("sales", lambda s: END if s["result"].get("status") == "REJECT" else "kyc")
    graph.add_conditional_edges("kyc", lambda s: "credit" if s["result"]["status"] == "VERIFIED" else END)
    graph.add_conditional_edges("credit", lambda s: "sanction" if s["result"]["status"] in
                                ("AUTO_APPROVE", "CONDITIONAL_APPROVE") else END)
    graph.add_edge("sanction", END)
    return graph.compile()
