#!/bin/bash

if [ -z "$1" ]; then
    echo "Foydalanish: $0 <domain_yoki_ip>"
    exit 1
fi

TARGET="$1"
WORDLIST="./scripts/common.txt"

if [ ! -f "$WORDLIST" ]; then
    echo "FATAL: Wordlist fayli topilmadi: $WORDLIST" >&2
    exit 1
fi

# 🔥 Localhost va Portlar bilan muammosiz ishlashi uchun:
# -S: Jimroq rejim (keraksiz ma'lumotlarni chiqarib tashlaydi)
# -r: Sub-papkalar ichiga chuqur kirmaslik (skan jarayonini tezlashtiradi)
dirb "$TARGET" "$WORDLIST" -S -r