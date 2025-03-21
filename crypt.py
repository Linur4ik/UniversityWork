from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os

def encrypt_aes128(bitstream: str, key: bytes) -> bytes:
    """Шифрование данных AES-128-CBC с PKCS7 паддингом"""
    # Генерация случайного IV
    original_bytes = int(bitstream, 2).to_bytes((len(bitstream) + 7) // 8, 'big')
    
    length_prefix = len(bitstream).to_bytes(4, 'big')  # 4 байта для длины

    data = length_prefix + original_bytes

    iv = os.urandom(16)
    
    # Добавление паддинга
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    
    # Шифрование
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    return iv + ciphertext

def decrypt_aes128(encrypted_data: bytes, key: bytes) -> str:
    """Дешифрование данных AES-128-CBC"""
    # Извлечение IV
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]
    
    # Дешифрование
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # Удаление паддинга
    unpadder = padding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
    
    length = int.from_bytes(unpadded_data[:4], 'big')  # Первые 4 байта — длина
    unpadded_data = unpadded_data[4:]  # Остальные байты — данные
    decrypted_bitstream = bin(int.from_bytes(unpadded_data, 'big'))[2:]
        
    # Дополняем нулями до исходной длины
    decrypted_bitstream = decrypted_bitstream.zfill(length)

    return decrypted_bitstream