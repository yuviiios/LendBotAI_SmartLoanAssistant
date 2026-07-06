import hashlib


class CreditScoreService:
    # Test PANs with fixed scores for deterministic test scenarios
    FIXED_SCORES = {
        "ABCDE1234F": 780,
        "PQRSX9999Z": 720,
        "LOWSC0000X": 650,
    }

    async def get_score(self, pan: str) -> int:
        if pan in self.FIXED_SCORES:
            return self.FIXED_SCORES[pan]

        # Deterministic score from PAN hash: same PAN → same score always
        # Range: 620-820 (realistic distribution)
        hash_val = int(hashlib.sha256(pan.encode()).hexdigest(), 16)
        return 620 + (hash_val % 201)  # 620 to 820
