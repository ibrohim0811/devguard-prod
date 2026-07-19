import re

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