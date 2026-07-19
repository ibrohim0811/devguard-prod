import re
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
    

