import re
import socket
import ipaddress
from urllib.parse import urlparse

def is_ip_private(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_reserved or
            ip.is_multicast or
            ip.is_unspecified
        )
    except ValueError:
        return True

def validate_safe_url_or_domain(url_or_domain: str) -> tuple[bool, str]:
    """
    Validates that a URL or domain does not point to internal/private networks or cloud metadata (SSRF prevention).
    Returns (is_safe, host_or_error_message).
    """
    if not url_or_domain:
        return False, "Bo'sh domen yoki URL!"

    raw = str(url_or_domain).strip()
    if not raw.startswith(('http://', 'https://')):
        url_to_parse = f"http://{raw}"
    else:
        url_to_parse = raw

    try:
        parsed = urlparse(url_to_parse)
        hostname = parsed.hostname
        if not hostname:
            return False, "Noto'g'ri domen nomi!"

        if hostname.lower() in ("169.254.169.254", "metadata.google.internal", "instance-data"):
            return False, "Manzilga ulanish rad etildi (Cloud Metadata Host)!"

        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info:
            return False, "Domen IP manzilini aniqlab bo'lmadi!"

        for item in addr_info:
            ip_str = item[4][0]
            if is_ip_private(ip_str):
                return False, f"Ichki/Xususiy IP manzilga so'rov yuborish rad etildi ({ip_str})!"

        return True, hostname
    except Exception as e:
        return False, f"Domen tekshirishda xatolik: {str(e)}"

def validate_phone_number(phone_number: str) -> str | None:
    # Faqat raqamlarni qoldiramiz
    clean_phone = re.sub(r'\D', '', str(phone_number))

    # Raqam uzunligini tekshirish va xalqaro kodni (998) yuklash
    if len(clean_phone) == 12 and clean_phone.startswith("998"):
        res = clean_phone
    elif len(clean_phone) == 9:
        res = "998" + clean_phone
    else:
        return None

    # O'zbekistondagi barcha faol mobil va shahar operatorlari prefikslari (2026-yil holatiga)
    # Beeline, Ucell, Mobiuz, Uztelecom, Humans va shahar raqamlari
    valid_prefixes = {
        # Mobil operatorlar
        '33', '88', '90', '91', '93', '94', '95', '97', '98', '99', 
        '20', '77', '50', '55', '70', '75', '10', '11', '12',
        # Shahar va hududiy raqamlar (ixtiyoriy, agar kerak bo'lsa)
        '71', '55', '61', '62', '65', '66', '67', '69', '72', '73', '74', '76', '79'
    }
    
    # Prefiksni tekshirish (3- va 4-indekslar)
    if res[3:5] in valid_prefixes:
        # Agar xohlasangiz, bu yerda "+" belgisi bilan qaytarishingiz mumkin: f"+{res}"
        return res
    
    return None

def validate_email(email):
    # Regex shablonimiz
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    # Tekshirish
    if re.match(email_regex, email):
        return True
    return False


DOMAIN_PATTERN = r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$"
SUBDOMAIN_PATTERN = r"^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$"

def is_subdomain(text):
    # Tozalash: agar foydalanuvchi adashib https:// yoki oxiriga / qo'shgan bo'lsa qirqamiz
    clean_text = text.replace("https://", "").replace("http://", "").split('/')[0]

    if re.match(DOMAIN_PATTERN, clean_text):
        return False
    elif re.match(SUBDOMAIN_PATTERN, clean_text):
        return True
    else:
        return "Noto'g'ri format!"