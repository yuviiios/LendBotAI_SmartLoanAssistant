# app/services/credit_score_service.py

#What will it do?
#Given a PAN → return a credit score
#No decision logic

class CreditScoreService:
    async def get_score(self, pan: str) -> int:
        # Mock implementation
        scores = {
            "ABCDE1234F": 780,
            "PQRSX9999Z": 720,
            "LOWSC0000X": 650,
        }
        return scores.get(pan, 700)
