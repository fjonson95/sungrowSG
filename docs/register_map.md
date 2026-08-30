# SG12RT registerkarta — status

**Inget här är verifierat.** Detta är en checklista och arbetsyta för att
bygga en pålitlig registerkarta, inte en källa att koda mot direkt.

## Att göra

1. Skaffa Sungrows officiella "Communication Protocol of Residential
   Hybrid Inverter and String Inverter (Modbus)" för SG5.0RT–SG12RT-
   familjen (via installatör/Sungrows partnerportal).
2. Jämför mot community-kartor:
   - https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant
     (SH-hybrid, INTE SG-sträng — bra referens men inte facit för SG12RT)
   - Eventuella publika mallar i TCzerny/ha-modbus-manager för SG-serien
3. Skanna en riktig SG12RT (t.ex. med `scripts/query.py` eller en generisk
   Modbus-scanner) och verifiera adress för adress.
4. Uppdatera `library/sungrow-modbus/src/sungrow_modbus/registers.py` och
   sätt `verified=True` per fält när det är bekräftat.

## Kända osäkerheter

- Bas-offset (0-baserad vs Sungrows 1-baserade dokumentnumrering).
- Vilka register som är `input` (FC04) vs `holding` (FC03/06/16) — kan
  skilja per firmware-version.
- Export-effektbegränsning och andra skrivbara register: **rör inte**
  förrän bekräftat, fel register kan koppla bort invertern från nätet.
