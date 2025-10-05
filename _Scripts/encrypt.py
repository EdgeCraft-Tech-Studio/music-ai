from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

# Your actual OpenAI key
api_key = "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"
key = b'NahaPatchio12345'  # ✅ 16 bytes – OK

# Pad the key (AES needs block size alignment)
def pad(s): return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
padded_key = pad(api_key).encode("utf-8")

# Encrypt
cipher = AES.new(key, AES.MODE_ECB)
encrypted = cipher.encrypt(padded_key)

# Base64-encode for storage
encrypted_base64 = base64.b64encode(encrypted).decode("utf-8")
print("Encrypted Key:", encrypted_base64)
