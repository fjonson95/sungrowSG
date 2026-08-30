# SG12RT registerkarta — status

**Verifierad mot Sungrows officiella protokolldokument, och spot-testad
live mot en riktig SG12RT** (senast 2026-08-30, `scripts/query.py` mot
`10.1.6.206:502`, unit-id 1). Alla input-registerfält i `registers.py` är
nu wired in i `models.py` och gav rimliga, verkliga värden vid senaste
körning — se `scripts/query.py`s utdata (körs mot din inverter, inte
återgivet i sin helhet här eftersom listan är lång; se fältlistan
nedan för vad som täcks).

Detta hittade två riktiga buggar under vägen (se "Word order"- och
`register_space`-avsnitten) — PDF-verifiering ensam hade inte fångat
dem.

## Källa

[bohdan-s/Sungrow-Inverter](https://github.com/bohdan-s/Sungrow-Inverter/blob/main/Modbus%20Information/Communication%20Protocol%20of%20PV%20Grid-Connected%20String%20Inverters_V1.1.37_EN.pdf)
speglar Sungrows officiella "Communication Protocol of PV Grid-Connected
String Inverters" (V1.1.37 EN). Varje fält i
`library/sungrow-modbus/src/sungrow_modbus/registers.py` är avläst direkt
ur det dokumentets registertabeller (avsnitt 3.1 "Running information",
avsnittet "a) Parameter setting" för skrivbara register) och Appendix 6
(enhetskoder).

## VIKTIGT: adress-offset (löst)

Dokumentets tabeller listar adresser som **1-baserade referensnummer**
(t.ex. "Device type code: 5000"), **inte** den 0-baserade adress man
skickar på wire. Dokumentet säger det uttryckligen ("Visit all registers
by subtracting 1 from the register address") och bevisar det med
räkneexempel i hex:

- "acquire data from address 5000" → PC skickar `0x1387` = **4999**
- "acquire SN ... from address starting from 4990" → skickar `0x137D` = **4989**
- "read data from address 5000 of 4x [holding] type" → skickar `0x1387` = **4999**
  (samma -1-regel gäller skrivbara/holding-register)

Detta bekräftas oberoende av `bohdan-s/SunGather`s faktiska klientkod
(`SungrowClient.py`, `SungrowClient`-paketet på PyPI): den lagrar
dokumentadressen i sin yaml men gör `register['address'] - 1` innan den
anropar pymodbus `read_input_registers`/`read_holding_registers`.

**Slutsats:** `registers.py` lagrar nu den riktiga 0-baserade
wire-adressen (dokumentadress − 1) i `RegisterSpec.address`, och
dokumentets egna nummer i `manufacturer_ref` (för spårbarhet). Tidigare
versioner av den här filen (och en tidigare passering i det här repot)
blandade ihop detta — se git-historik om ni undrar varför adresserna
ändrats fram och tillbaka.

## VIKTIGT: word order på 32-bitars fält (löst, hårdvarubekräftat)

Dokumentet säger inget om byte-/word-ordning för U32/S32-fält (t.ex.
`total_active_power`, `total_power_yield`). `modbus_connection`s
`uint32()` antar `word_order="big"` (högsta ordets register kommer
först) som default. Mot den riktiga SG12RT:n gav det:

- `total_active_power`: **99 418 112 W** (99 MW — orimligt för en 12kW-inverter)
- `total_power_yield`: **359 720 550,9 kWh** (360 GWh — orimligt för en
  hushållsinverter)

Rålästa register (`read_input_registers`) för `total_active_power`
(wire-adress 5030, 2 register) gav `[1457, 0]` — dvs **lågordet ligger
på den första/lägre adressen**, motsatsen till "big". Med
`word_order="little"` blev värdena rimliga (se exemplet ovan: 1317 W,
38256.9 kWh). Alla `uint32()`-fält i `models.py` har nu
`word_order="little"` explicit. Detta är specifikt bekräftat för denna
inverter över Modbus TCP (troligen samma dongle-/firmware-kvirk som
andra community-projekt möter) — inte nödvändigtvis universellt för
alla Sungrow-modeller/anslutningssätt, men gäller garanterat SG12RT över
TCP såsom testat här.

## Vad som är verifierat mot PDF:en

Läs = FC04 (input registers), Skriv = FC03/06/16 (holding registers).
Kolumnen "Wire-adress" är vad som faktiskt skickas (= dokumentadress − 1,
vad `RegisterSpec.address` innehåller); "Dok.-adress" är numret som står
i Sungrows tabell (`manufacturer_ref`).

| Fält | Dok.-adress | Wire-adress | Funktion | Typ | Skala | Enhet |
|---|---|---|---|---|---|---|
| serial_number | 4990-4999 | 4989 (10 reg) | Läs | UTF-8 | – | – |
| device_type_code | 5000 | 4999 | Läs | U16 | – | – (0x2434 = SG12RT) |
| nominal_active_power | 5001 | 5000 | Läs | U16 | 0.1 | kW |
| output_type | 5002 | 5001 | Läs | U16 | – | enum |
| daily_power_yield | 5003 | 5002 | Läs | U16 | 0.1 | kWh |
| total_power_yield (legacy) | 5004-5005 | 5003 (2 reg) | Läs | U32 | 1 | kWh |
| total_running_time | 5006-5007 | 5005 (2 reg) | Läs | U32 | 1 | h |
| internal_temperature | 5008 | 5007 | Läs | S16 | 0.1 | °C |
| total_apparent_power | 5009-5010 | 5008 (2 reg) | Läs | U32 | 1 | VA |
| mppt_1_voltage / current | 5011 / 5012 | 5010 / 5011 | Läs | U16 | 0.1 | V / A |
| mppt_2_voltage / current | 5013 / 5014 | 5012 / 5013 | Läs | U16 | 0.1 | V / A |
| total_dc_power | 5017-5018 | 5016 (2 reg) | Läs | U32 | 1 | W |
| phase_a/b/c_voltage | 5019/5020/5021 | 5018/5019/5020 | Läs | U16 | 0.1 | V |
| phase_a/b/c_current | 5022/5023/5024 | 5021/5022/5023 | Läs | U16 | 0.1 | A |
| total_active_power | 5031-5032 | 5030 (2 reg) | Läs | U32 | 1 | W |
| total_reactive_power | 5033-5034 | 5032 (2 reg) | Läs | S32 | 1 | Var |
| power_factor | 5035 | 5034 | Läs | S16 | 0.001 | – |
| grid_frequency | 5036 | 5035 | Läs | U16 | 0.1 | Hz |
| work_state_1 | 5038 | 5037 | Läs | U16 | – | enum |
| nominal_reactive_power | 5049 | 5048 | Läs | U16 | 0.1 | kVar |
| array_insulation_resistance | 5071 | 5070 | Läs | U16 | 1 | kΩ |
| work_state_2 | 5081-5082 | 5080 (2 reg) | Läs | U32 | – | bitmask |
| total_power_yield (RT-familjen, exakt) | 5144-5145 | 5143 (2 reg) | Läs | U32 | 0.1 | kWh |
| string_1/2/3_current | 7013/7014/7015 | 7012/7013/7014 | Läs | U16 | 0.01 | A |
| meter_power | 5083-5084 | 5082 (2 reg) | Läs | S32 | 1 | W |
| meter_a/b/c_phase_power | 5085-5090 | 5084/5086/5088 (2 reg vardera) | Läs | S32 | 1 | W |
| load_power | 5091-5092 | 5090 (2 reg) | Läs | S32 | 1 | W |
| daily/total_export_energy | 5093-5096 | 5092/5094 (2 reg vardera) | Läs | U32 | 0.1 | kWh |
| daily/total_import_energy | 5097-5100 | 5096/5098 (2 reg vardera) | Läs | U32 | 0.1 | kWh |
| daily/total_direct_energy_consumption | 5101-5104 | 5100/5102 (2 reg vardera) | Läs | U32 | 0.1 | kWh |
| protocol_version | 4952-4953 | 4951 (2 reg) | Läs | U32 | – | Major.Minor.Patch.Build-bytes, ej skala (se not nedan) |
| negative_voltage_to_ground | 5146 | 5145 | Läs | S16 | 0.1 | V |
| bus_voltage | 5147 | 5146 | Läs | U16 | 0.1 | V |
| start_stop | 5006 | 5005 | Skriv | U16 | – | enum (0xCF=start, 0xCE=stop) |
| power_limitation_switch | 5007 | 5006 | Skriv | U16 | – | enum (0xAA=enable, 0x55=disable) |
| power_limitation_setting | 5008 | 5007 | Skriv | U16 | 0.1 | % |
| night_svg_switch | 5035 | 5034 | Skriv | U16 | – | enum (0xAA=enable, 0x55=disable) |

SG12RT har **2 MPPT-ingångar** (bekräftat i Appendix 6, device code
`0x2434`) — `mppt_3_voltage`/`mppt_3_current` m.fl. finns i kartan för
större SG-modeller men gäller inte SG12RT.

Samtliga device-typkoder för RT-familjen i `const.py` (`0x243D`–`0x2437`
för SG3.0RT–SG20RT) är avlästa direkt ur Appendix 6.

### Per-sträng ström (inte spänning) — 2026-08-30

Sungrow SG-seriens protokoll rapporterar **bara ström per sträng, aldrig
spänning**. Strängar på samma MPPT är parallellkopplade och delar
spänning — den mäts per MPPT (`mppt_1_voltage`/`mppt_2_voltage`), inte
per sträng. Det finns inget "string voltage"-register i det officiella
dokumentet — inte en lucka i den här filen, utan hur hårdvaran fungerar.

Appendix 6 anger SG12RT:s "String/MPPT" som **"2;1"**: MPPT 1 har 2
strängar, MPPT 2 har 1 sträng — 3 strängar totalt
(`string_1_current`/`string_2_current` på MPPT 1, `string_3_current` på
MPPT 2), adress 7013-7015 (dok) / 7012-7014 (wire). Dokumentet varnar:
"If the value of string/MPPT is 1, it indicates that no string
information (7013-7036) is uploaded" — gäller inte SG12RT (värdet är
"2;1", inte "1"). Live-testat 2026-08-30, gav rimliga strömvärden
(0.76 A, 0.0 A, 1.04 A).

### Elmätare (extern CT/smart meter) — 2026-08-30

Dokumentets egen "Valid for inverters"-lista på det här blocket
(5083-5104) nämner bara SG5KTL-MT/SG6KTL-MT/SG8KTL-M/SG10KTL-M/
SG10KTL-MT/SG12KTL-M/SG15KTL-M/SG17KTL-M/SG20KTL-M — **inte** RT-familjen
SG12RT tillhör. Testat live ändå (2026-08-30) och fick fullt rimliga,
internt konsistenta värden: `meter_a_phase_power + meter_b_phase_power +
meter_c_phase_power` summerade exakt till `meter_power` varje gång, och
export/import-energin låg i rimlig storleksordning relativt
`total_power_yield`. Behandla som fungerande på den här enheten (har
tydligen en CT/mätare inkopplad); en SG12RT utan mätartillbehör kan
tänkas läsa nollor här istället för fel.

### Jordfelsspänning, bus-spänning, Night SVG — 2026-08-30

Alla tre direkt ur samma officiella SG-PDF (sidor jag inte läst klart
förrän nu): `negative_voltage_to_ground` (doc 5146, S16, 0.1V - jordfels-
/isolationsövervakning) och `bus_voltage` (doc 5147, U16, 0.1V - DC-bus-
spänningen inne i invertern). `night_svg_switch` (doc 5035, **holding**-
register, 0xAA/0x55 enable/disable) styr en reaktiv-effekt-funktion
("SVG" = Static Var Generator) nattetid - dokumentet listar SG12RT
uttryckligen i "Valid for inverters". Live-testat 2026-08-30:
`negative_voltage_to_ground=0.0V` (inget jordfel, väntat),
`bus_voltage≈679-680V` (normalt för en strängväxelriktare),
`night_svg_switch=0x55` (Disable - rimligt default/installatörsval).
`night_svg_switch` är inte kopplad in i `SungrowSGInverter` (samma skäl
som `start_stop`/`power_limitation_*`: den ligger i holding-registerrymden,
och klassen är input-only, se `register_space`-kommentaren i
`models.py`) - metadata finns i `registers.py` för när/om en andra
Component för holding-läsning byggs.

### Protokollversion — inte i SG-PDF:en, men i annan Sungrow-dokumentation — 2026-08-30

Doc-adress 4952-4953 är markerad **"Reserved"** i den officiella
SG-sträng-PDF:en som resten av den här filen bygger på (se "Källa" ovan)
— det finns inget "Modbus protocol version"-register där för
strängväxelriktare. Fältet kommer istället från annan Sungrow-
dokumentation (samma adress dokumenterad som `protocol_version` i
SH-hybridseriens protokoll, format `0x01015300 = V1.1.53`
Major.Minor.Patch.Build, med noten "Logger forwarding not supported" —
dvs vissa datalogger-/gateway-uppsättningar vidarebefordrar inte fältet).

Live-testat 2026-08-30 med samma `word_order="little"`-konvention som
resten av U32-fälten i den här filen: avkodades till `0x01011900` =
**V1.1.25.0** — en punktrelease under V1.1.37-dokumentet den här filen
i övrigt bygger på, rimligt för en inverter med något äldre firmware än
senaste protokolldokumentet. `models.py` exponerar både råvärdet
(`protocol_version_raw`) och en formaterad `protocol_version`-property.

Sedan tidigare vet vi också att det reserverade blocket 4950-4989 i
övrigt innehåller läsbar ASCII-text som ser ut som
firmware-versionstaggar (`"...LCD_BERYL-S_V11_V01_A"`,
`"...DSP_BERYL-S_V11_V01_A"`) — dessa är fortfarande INTE tillagda
någonstans, helt odokumenterade och fältgränserna rena gissningar. Säg
till om ni vill ha dem inlagda ändå.

## Att göra

1. ~~Skanna community-kartor~~ — klart.
2. ~~Läs officiella PDF:en register-för-register~~ — klart, se ovan.
   `RegisterSpec.verified=True` är satt i `registers.py` för alla fält
   som kontrollerats mot dokumentet.
3. ~~Testa mot en riktig SG12RT~~ — klart, se ovan.
4. ~~Koppla in resten av de PDF-verifierade input-registerfälten i
   `models.py`~~ — klart (2026-08-30): `nominal_active_power`,
   `output_type`, `total_running_time`, `internal_temperature`,
   `total_apparent_power`, `mppt_1/2_voltage/current`, `total_dc_power`,
   `phase_a/b/c_current`, `total_reactive_power`, `power_factor`,
   `grid_frequency`, `work_state_1/2`, `nominal_reactive_power`,
   `array_insulation_resistance`. Alla count=2-fält fick
   `word_order="little"` (inte defaultens `"big"`) och alla gav rimliga
   värden vid livetest — se `scripts/query.py`. `array_insulation_resistance`
   använder `nan=0xFFFF` per dokumentets "0xFFFF = invalid"-not, så en
   ogiltig avläsning blir `None` istället för en orimlig 6553.5 kΩ.
5. **Kvarstår:** de skrivbara holding-registren
   (`start_stop`/`power_limitation_switch`/`power_limitation_setting`/
   `night_svg_switch`) ligger fortfarande bara som metadata i
   `registers.py`, inte wired in någonstans som skrivbara — de kräver en
   egen `Component` (annan `register_space`) och ska INTE röras mot en
   aktiv inverter utan att vara medveten om vad de gör: fel värde kan
   koppla bort invertern från nätet eller stoppa produktionen.
6. HA-integrationen (`custom_components/sungrow_sg/`) är fortfarande
   skelett och exponerar bara de sex ursprungliga fälten som sensorer —
   uppdatera `coordinator.py`/`sensor.py` för att plocka upp alla fält
   som nu finns i `SungrowSGInverter`.

## Kända osäkerheter

- Bara fälten som är wired in i `models.py` (se punkt 3 ovan) är faktiskt
  lästa mot riktig hårdvara. Resten av `registers.py` är PDF-verifierat
  men inte hårdvarutestat — se punkt 4 ovan. Word-order-fällan (löst ovan)
  visar att PDF-verifiering ensam inte räcker för count=2-fält.
- Mätarblocket (`meter_*`, `daily/total_export/import_energy`) fungerar
  på den här specifika SG12RT:n trots att dokumentet säger att det inte
  gäller RT-familjen — okänt om det beror på nyare firmware, en generellt
  omodern doc-lista, eller att just den här enheten har en CT/mätare
  inkopplad som gör skillnaden. En annan SG12RT kan bete sig annorlunda.
- De skrivbara registren är läst ur samma officiella dokument som
  läs-registren, men är **inte** wired in i `models.py` som skrivbara
  ännu — lämnas avsiktligt utkommenterade tills bekräftat mot hårdvara.
- ~~Vilket dataformat `modbus_connection`s `gauge()`/`uint32()`-hjälpare
  faktiskt förväntar sig~~ — bekräftat: paketet är installerat (Python
  3.13, `pip install "modbus-connection[tmodbus]"`) och adresserna i
  `registers.py` är 0-baserade wire-adresser, precis som antaget.
  Bekräftelsen avslöjade en riktig bugg på vägen: `Component` läser från
  holding-register (FC03) som default, men hela den här registerkartan
  ligger i input-registerrymden (FC04) — `models.py` satte inte
  `register_space = "input"`, vilket hade gjort att varje läsning mot en
  riktig inverter träffat fel registerfil. Fixat och täckt av
  `library/sungrow-modbus/tests/test_models.py::test_reads_target_the_input_register_space`.
