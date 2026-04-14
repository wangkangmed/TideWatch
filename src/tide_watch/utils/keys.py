"""由 scope + provider + external_id 生成稳定幂等键。"""


def make_idempotency_key(salt: str, provider_id: str, external_id: str) -> str:
    return f"{salt}:{provider_id}:{external_id}"
