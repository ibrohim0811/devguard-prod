#!/bin/bash

if [ -z "$1" ]; then
    echo "Foydalanish: $0 <domain_yoki_ip>"
    exit 1
fi

RAW_TARGET=$1

# Domenni tozalash (http/https va sleshlarni olib tashlash)
TARGET=$(echo "$RAW_TARGET" | sed -e 's/^https:\/\///' -e 's/^http:\/\///' -e 's/\/.*$//')

# 🔥 DIRB ga wordlist manzilini aniq ko'rsatamiz va URL formatida yuboramiz
# (dirb ishlashi uchun target boshida http:// bo'lishi shart, shuning uchun qayta qo'shamiz)
dirb "http://$TARGET" /usr/share/dirb/wordlists/common.txt