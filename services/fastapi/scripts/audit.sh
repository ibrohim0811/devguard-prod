#!/bin/bash

if [ -z "$1" ]; then

    echo "Foydalanish: $0 <domain_yoki_ip>"

    exit 1

fi


RAW_TARGET=$1




TARGET=$(echo "$RAW_TARGET" | sed -e 's/^https:\/\///' -e 's/^http:\/\///' -e 's/\/.*$//')



DATE=$(date +"%Y%m%d_%H%M%S")




echo "[*] Kengaytirilgan audit boshlanmoqda: $TARGET"

echo "--------------------------------------------------"




echo "[*] 1/5 Nmap skaneri ishlamoqda..."

nmap -sV -sC "$TARGET" 




echo "[*] 2/5 Nikto skaneri ishlamoqda..."

nikto -h "$RAW_TARGET" -Tuning 123bde 




echo "[*] 3/5 SQLMap tekshiruvi ishlamoqda..."

sqlmap -u "$RAW_TARGET" --batch --crawl=2 --level=1 --risk=1 


if [[ $TARGET != http* ]]; then
   URL="https://$TARGET"
else
   URL=$TARGET
fi

nuclei -u "$URL" -as


echo "[+] Barcha testlar to'liq yakunlandi!"
