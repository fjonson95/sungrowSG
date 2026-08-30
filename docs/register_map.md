# SG12RT registerkarta — status

**Verifierad mot Sungrows officiella protokolldokument, och spot-testad
live mot en riktig SG12RT** (senast 2026-08-30, `scripts/query.py` mot
`10.1.6.206:502`, unit-id 1). Alla input-registerfält i `registers.py` är
nu wired in i `models.py` och gav rimliga, verkliga värden vid senaste
körning — se `scripts/query.py`s utdata (körs mot din inverter, inte
återgivet i sin helhet här eftersom listan är lång; se fältlistan
nedan för vad som täcks).

Detta hittade tre riktiga buggar under vägen (se "Word order"-,
`register_space`- och `total_active_power`-avsnitten) — PDF-verifiering
ensam hade inte fångat dem alla; den sista hittades först vid en andra
genomgång mot ett nyare, mer exakt dokument (V1.1.80).

## Källa

Två officiella dokument, i tidsordning:

1. [bohdan-s/Sungrow-Inverter](https://github.com/bohdan-s/Sungrow-Inverter/blob/main/Modbus%20Information/Communication%20Protocol%20of%20PV%20Grid-Connected%20String%20Inverters_V1.1.37_EN.pdf)
   speglar Sungrows "Communication Protocol of PV Grid-Connected String
   Inverters" (V1.1.37 EN) — den ursprungliga källan för nästan alla fält
   nedan (avsnitt 3.1 "Running information", "a) Parameter setting" för
   skrivbara register, Appendix 6 för enhetskoder).
2. **"Communication Protocol of Residential & Commercial PV
   Grid-Connected Inverters" (V1.1.80, 2026-03-27)** — en nyare, enhetlig
   PDF som ersätter V1.1.37 och täcker alla Sungrow-familjer via en
   gemensam Appendix 1. Hittad och genomgången 2026-08-30. Bekräftar
   word-order- och adress-offset-reglerna nedan **explicit i klartext**
   (tidigare bara hårdvarubekräftat empiriskt), och gav en riktig bugg-
   fix (se "total_active_power" i tabellen nedan) samt fler enhetskoder
   för RT-familjens regionvarianter (Australien, -P2).

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

## VIKTIGT: word order på 32-bitars fält (löst, hårdvaru- OCH dokumentbekräftat)

V1.1.37-dokumentet (som resten av det här avsnittet handlar om) säger
inget om byte-/word-ordning för U32/S32-fält (t.ex. `total_active_power`,
`total_power_yield`). Det nyare V1.1.80-dokumentet gör det däremot,
uttryckligen (avsnitt 1.1 Abbreviations): "U32: 32-bit unsigned integer;
little-endian for double-word data. Big-endian for byte data." — dvs
precis det som hittades empiriskt nedan är dokumenterat beteende, inte en
den här enhetens/dongelns kvirk. `modbus_connection`s `uint32()` antar
`word_order="big"` (högsta ordets register kommer först) som default. Mot
den riktiga SG12RT:n gav det:

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

Input- och holding-register är helt separata adressrymder i Modbus (FC04
resp. FC03/06/16) - samma nummer kan alltså dyka upp i båda tabellerna
utan att vara en kollision (t.ex. doc-adress 5006/5008 finns i båda:
`total_running_time`/`internal_temperature` som läsbara input-register,
`start_stop`/`power_limitation_setting` som skrivbara holding-register).
Båda tabellerna är sorterade i stigande dok.-adressordning. Kolumnen
"Wire-adress" är vad som faktiskt skickas (= dokumentadress − 1, vad
`RegisterSpec.address` innehåller); "Dok.-adress" är numret som står i
Sungrows tabell (`manufacturer_ref`).

### Input-register (FC04, läsning)

| Fält | Dok.-adress | Wire-adress | Typ | Skala | Enhet |
|---|---|---|---|---|---|
| protocol_no | 4950-4951 | 4949 (2 reg) | U32 | – | Betydelse odokumenterad (se not nedan) |
| protocol_version | 4952-4953 | 4951 (2 reg) | U32 | – | Major.Minor.Patch.Build-bytes, ej skala (se not nedan) |
| arm_software_version | 4954-4968 | 4953 (15 reg) | UTF-8 | – | (se not nedan) |
| dsp_software_version | 4969-4983 | 4968 (15 reg) | UTF-8 | – | (se not nedan) |
| serial_number | 4990-4999 | 4989 (10 reg) | UTF-8 | – | – |
| device_type_code | 5000 | 4999 | U16 | – | – (0x2434 = SG12RT) |
| nominal_active_power | 5001 | 5000 | U16 | 0.1 | kW |
| output_type | 5002 | 5001 | U16 | – | enum |
| daily_power_yield | 5003 | 5002 | U16 | 0.1 | kWh |
| total_power_yield (legacy) | 5004-5005 | 5003 (2 reg) | U32 | 1 | kWh |
| total_running_time | 5006-5007 | 5005 (2 reg) | U32 | 1 | h |
| internal_temperature | 5008 | 5007 | S16 | 0.1 | °C |
| total_apparent_power | 5009-5010 | 5008 (2 reg) | U32 | 1 | VA |
| mppt_1_voltage / current | 5011 / 5012 | 5010 / 5011 | U16 | 0.1 | V / A |
| mppt_2_voltage / current | 5013 / 5014 | 5012 / 5013 | U16 | 0.1 | V / A |
| total_dc_power | 5017-5018 | 5016 (2 reg) | U32 | 1 | W |
| phase_a/b/c_voltage | 5019/5020/5021 | 5018/5019/5020 | U16 | 0.1 | V |
| phase_a/b/c_current | 5022/5023/5024 | 5021/5022/5023 | U16 | 0.1 | A |
| total_active_power | 5031-5032 | 5030 (2 reg) | S32 | 1 | W |
| total_reactive_power | 5033-5034 | 5032 (2 reg) | S32 | 1 | Var |
| power_factor | 5035 | 5034 | S16 | 0.001 | – |
| work_state_1 | 5038 | 5037 | U16 | – | enum |
| fault_alarm_year/month/day/hour/minute/second | 5039-5044 | 5038-5043 | U16 vardera | – | Endast giltiga när work_state_1 = fault/alarm |
| fault_alarm_code | 5045 | 5044 | U16 | – | Se Appendix 4-tabellen nedan |
| nominal_reactive_power | 5049 | 5048 | U16 | 0.1 | kVar |
| array_insulation_resistance | 5071 | 5070 | U16 | 1 | kΩ |
| work_state_2 | 5081-5082 | 5080 (2 reg) | U32 | – | bitmask |
| meter_power | 5083-5084 | 5082 (2 reg) | S32 | 1 | W |
| meter_a/b/c_phase_power | 5085-5090 | 5084/5086/5088 (2 reg vardera) | S32 | 1 | W |
| load_power | 5091-5092 | 5090 (2 reg) | S32 | 1 | W |
| daily/total_export_energy | 5093-5096 | 5092/5094 (2 reg vardera) | U32 | 0.1 | kWh |
| daily/total_import_energy | 5097-5100 | 5096/5098 (2 reg vardera) | U32 | 0.1 | kWh |
| daily/total_direct_energy_consumption | 5101-5104 | 5100/5102 (2 reg vardera) | U32 | 0.1 | kWh |
| daily_running_time | 5113 | 5112 | U16 | 1 | min |
| monthly_power_yield | 5128-5129 | 5127 (2 reg) | U32 | 0.1 | kWh |
| total_power_yield (RT-familjen, exakt) | 5144-5145 | 5143 (2 reg) | U32 | 0.1 | kWh |
| negative_voltage_to_ground | 5146 | 5145 | S16 | 0.1 | V |
| bus_voltage | 5147 | 5146 | U16 | 0.1 | V |
| grid_frequency | 5148 | 5147 | U16 | 0.01 | Hz (se not nedan om 5036) |
| string_1/2/3_current | 7013/7014/7015 | 7012/7013/7014 | U16 | 0.01 | A |

### Holding-register (FC03/06/16, läs- och skrivbara)

| Fält | Dok.-adress | Wire-adress | Typ | Skala | Enhet |
|---|---|---|---|---|---|
| start_stop | 5006 | 5005 | U16 | – | enum (0xCF=start, 0xCE=stop) |
| power_limitation_switch | 5007 | 5006 | U16 | – | enum (0xAA=enable, 0x55=disable) |
| power_limitation_setting | 5008 | 5007 | U16 | 0.1 | % |
| feed_in_power_limit_switch | 5010 | 5009 | U16 | – | enum (0xAA=enable, 0x55=disable) |
| feed_in_power_limit_value | 5011 | 5010 | U16 | 0.01 | kW |
| feed_in_power_limit_ratio | 5015 | 5014 | U16 | 0.1 | % |
| power_limitation_adjustment | 5039 | 5038 | U16 | 0.1 | kW |
| night_svg_switch | 5035 | 5034 | U16 | – | enum (0xAA=enable, 0x55=disable) |

Alla åtta ovan är skrivbara (`RegisterSpec.writable=True`) och wired in i
`SungrowSGControl` (`register_space = "holding"`) - se
"skrivbara holding-register"-avsnittet i "Att göra" nedan för status.

**`total_active_power` var felaktigt `uint32()` (skulle vara `int32()`)**
— hittat 2026-08-30 vid genomgång av V1.1.80-dokumentet, som listar
5031-5032 som `S32` explicit (V1.1.37 hade ingen tydlig typmarkering här
som fångades vid ursprunglig genomgång). Fixat i `models.py`. Spelar roll
eftersom invertern kan rapportera kortvarigt negativ aktiv effekt vid
vissa fel-/vänteläges-övergångar — som `uint32` hade det wrappat till ett
orimligt stort positivt värde istället för ett litet negativt.

SG12RT har **2 MPPT-ingångar** (bekräftat i Appendix 1, device code
`0x2434`) — `mppt_3_voltage`/`mppt_3_current` m.fl. finns i kartan för
större SG-modeller men gäller inte SG12RT.

Samtliga device-typkoder för RT-familjen i `const.py` (`0x243D`–`0x2439`
för SG3.0RT–SG25RT) är avlästa direkt ur Appendix 1. Sungrow återanvänder
samma modellnamn (t.ex. "SG12RT") över flera regionvarianter med olika
device-typkoder — V1.1.80s Appendix 1 listar en "Overseas"-standardvariant
och en separat "Australian"-variant per effektklass, plus "-20"/"-P2"-
hårdvaruvarianter. Vår enhet läser `0x2434` (Overseas-standard, matchar
även Kina-varianten "SG12RT-20") — `0x2481` (Australien) och `0x2444`
(-P2) är andra RT-enheter som andra användare av biblioteket kan ha,
tillagda i `const.py` med samma modellnamn eftersom skillnaden bara
gäller effektbegränsningens tillåtna intervall, som det här biblioteket
inte styr mot.

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

### Appendix 2/3 (Working State 1/2) — 2026-08-30

Genomgångna för första gången (tidigare bara refererade, aldrig lästa i
sin helhet):

- **Appendix 2 (Table 10, `work_state_1`)**: hittade ett saknat värde -
  `0x1111` = "Uninitialized" - tillagt i `WORK_STATE_1_LABELS`
  (`const.py`). Övriga 11 värden stämde redan.
- **Appendix 3 (Table 11, `work_state_2`)**: bekräftar att `work_state_2`
  är en **bitmask**, inte en enum - dokumentet säger uttryckligen "The
  definition corresponding to the state is the same as that in Appendix
  2", dvs bit 0-13 är samma tillstånd som `work_state_1` fast som
  enskilda bitar (redundant mot `work_state_1_label`, avkodas inte
  separat). De två unika, användbara bitarna är summeringsbitarna:
  **bit 17** ("Device is grid-connected running") och **bit 18** ("Device
  is in fault stop state"). Live-exemplet från tidigare i sessionen
  (`0x20001`) är nu förklarat: bit 0 (run) + bit 17 (grid-connected).

  Tillagt som två beräknade properties i `models.py`
  (`is_grid_connected`, `is_in_fault`) och en ny `binary_sensor.py`-
  plattform i HA-integrationen (device_class `connectivity` respektive
  `problem`) - lämpligare entitetstyp för booleaner än en text-sensor.

### Kapitel 3 "Power Regulation Parameters" — styrsekvenser och nya register, 2026-08-30

V1.1.80 har ett helt kapitel (3.1 Active Power Regulation, 3.2 Reactive
Power Regulation) som beskriver **hur** styrningen ska sekvenseras, inte
bara adresserna - något vi inte läst igenom förrän nu.

**Viktig sekvens-info för register vi redan hade (`power_limitation_switch`/
`power_limitation_setting`):** `power_limitation_setting` (5008) är bara
verksam när `power_limitation_switch` (5007) redan är aktiverad (0xAA) -
dokumentets metod är uttryckligen tvåstegs: 1) aktivera switchen, 2) sätt
värdet. Vår kod skriver fälten oberoende av varandra (ingen
ordningskontroll i `SungrowSGControl`), så en integratör måste själv
aktivera switchen först. Efter en omstart av invertern **återställs
effektbegränsningen till default** om man inte separat aktiverat "Active
Power Setting Persistence" via Sungrows app (finns inget Modbus-register
för det - bara i appen).

**Nytt, nu implementerat** (användaren valde dessa två grupper 2026-08-30):

- **`power_limitation_adjustment`** (doc 5039, 0.1kW) - alternativ till
  `power_limitation_setting`s procentvärde: sätter effektgränsen som ett
  absolut kW-värde istället. Samma precondition (`power_limitation_switch`
  måste vara på).
- **Feed-in power limit-familjen** (`feed_in_power_limit_switch` 5010,
  `feed_in_power_limit_value` 5011 i kW, `feed_in_power_limit_ratio` 5015
  i %) - en **separat kontrollpunkt** vid nätanslutningspunkten (Point A i
  dokumentets figur 1), skild från `power_limitation_*` som styr vid
  inverterns egen AC-utgång (Point B). Kräver en extern smart-mätare
  inkopplad för att vara meningsfull. Explicit listad som giltig för
  SG3.0-25RT-familjen, som SG12RT tillhör.

**Medvetet INTE implementerat** (användaren valde att bara dokumentera,
inte wire in, dessa - kan läggas till senare om det behövs):

- **Active Power Overload** (5020, 0xAA/0x55) - ändrar referensvärdet
  `power_limitation_setting`s procent räknas mot (rated vs max effekt).
- **All reaktiv-effekt-reglering** (kapitel 3.2, Table 6):
  `reactive_power_adjustment_mode` (5036, växlar mellan av/PF/ratio/Q(P)-
  kurva/Q(U)-kurva), `pf_setting` (5019), `reactive_power_percentage_
  setting` (5037), `reactive_power_adjustment` (5040, absolut kVar), plus
  Q(P)-kurva 1/2 (5048-5077, 5116-5134) och Q(U)-kurva 1/2 (5078-5115,
  5135-5154) - stora egna parameterblock (se Appendix 6-9), inte bara
  enkla enum/skalvärden.

### Felkoder (Appendix 4) — 2026-08-30

Fanns tidigare inte wired in alls: `fault_alarm_year/month/day/hour/
minute/second` (doc 5039-5044) och `fault_alarm_code` (doc 5045) - enligt
dokumentet giltiga "only when the device work state is fault (0x5500) or
alarm (0x9100)". `fault_alarm_code` slår upp Appendix 4 "Device Fault
Code" (Table 12), en tabell med ~30 unika felnamn mappade från hundratals
enskilda koder/intervall (t.ex. "2, 3, 14, 15" → "Grid Overvoltage").
Transkriberad ordagrant från V1.1.80 till `const.py`
(`FAULT_CODE_LABELS`) - **inte hårdvarutestad** (kräver att man faktiskt
framkallar ett fel på en riktig inverter, vilket inte görs här). En kod
som saknas i tabellen ger `"unknown"`, aldrig en gissning eller krasch.

`models.py` exponerar två beräknade properties istället för de råa
fälten: `fault_alarm_time` (formaterad `"YYYY-MM-DD HH:MM:SS"`, `None`
om år=0) och `fault_alarm_label` (uppslaget felnamn, `None` om kod=0).
Wired in som två diagnostiska textsensorer i HA-integrationen.

### Cross-check mot iSolarCloud — 2026-08-30

Användaren delade en live-skärmdump från **iSolarCloud** (Sungrows eget
moln-UI för den här specifika SG12RT:n, kväll/standby-läge). Resultat:

- Bekräftade nätfrekvens-fyndet nedan (49.99 Hz → högupplöst register).
- **"Daily operating time" (837 min) och "Yield this month" (1.7 MWh)**
  matchade två register vi missat: `daily_running_time` (doc 5113) och
  `monthly_power_yield` (doc 5128-5129) — nu tillagda, se tabellen ovan.
- **"Yield this year" (11.3 MWh) finns inte som Modbus-register** i
  dokumentet — det är ett molnsidesberäknat värde hos Sungrow, inte
  tillgängligt lokalt över Modbus. Ingen ny fält-mappning möjlig här.
- **Per-sträng-spänning i iSolarCloud (421.5 V för alla tre strängar)**
  är INTE ett Modbus-register — dokumentets 7013-7036-block innehåller
  bara STRÖM per sträng (se avsnittet "Per-sträng ström" ovan). Att
  UI-värdet (421.5V) skilde sig från den samtidigt visade MPPT-spänningen
  (412.3V) bekräftar att det är en molnsidesberäkning/annan källa, inte
  bara en direkt-vidarebefordrad MPPT-spänning. Bekräftar att vår
  tidigare slutsats (bara ström per sträng är läsbart) fortfarande
  stämmer.
- Firmware-strängarna i "Device information" (`LCD_BERYL-S_V11_V01_A`,
  `MDSP_BERYL-S_V11_V01_A`) matchar formatet vi förväntar oss av
  `arm_software_version`/`dsp_software_version` (se avsnittet om
  protokollnummer nedan) - ännu inte läst live mot de nya fälten, men
  ett gott tecken att de kommer avkodas rimligt.
- Övriga värden (spänningar, isolationsresistans 1964 kΩ, total
  produktion 38.3 MWh) var internt konsistenta med redan wired-in fält -
  inga fler avvikelser hittade.

### Nätfrekvens bytt till högupplöst register — 2026-08-30

Upptäckt genom att jämföra vår sensor mot **iSolarCloud** (Sungrows eget
moln-UI) live: iSolarCloud visade `49.99 Hz`, vår sensor skulle ha visat
`50.0 Hz`. Orsak: dokumentet listar `grid_frequency` på **två** adresser
med samma värde men olika upplösning — dok 5036 (`0.1Hz`, vad vi
tidigare läste) och dok 5148 (`0.01Hz`), med noten "Compared with 'Grid
frequency' 5148, only the resolution is different." iSolarCloud läser
uppenbarligen 5148. Bytt `GRID_FREQUENCY` i `registers.py` till adress
5148 (wire 5147, `scale=0.01`) — samma fältnamn i `models.py`, bara
källadressen ändrad. 5036 lämnas odokumenterad i koden (samma värde, bara
grövre) snarare än som ett eget fält.

### Protokollnummer + ARM/DSP-mjukvaruversion — nyupptäckt i V1.1.80, 2026-08-30

Vad som tidigare (V1.1.37, se avsnittet ovan) bara var ett odokumenterat
"Reserved"-block med läsbar ASCII-text (firmware-versionstaggar som
`"...LCD_BERYL-S_V11_V01_A"`, `"...DSP_BERYL-S_V11_V01_A"`, hittade live
2026-08-30 men med rena gissningar på fältgränser) visar sig vara
officiellt dokumenterat i V1.1.80s Table 3:

| Fält | Dok.-adress | Wire-adress | Typ | Not |
|---|---|---|---|---|
| protocol_no | 4950-4951 | 4949 (2 reg) | U32 | Betydelse utöver registertabellen odokumenterad |
| protocol_version | 4952-4953 | 4951 (2 reg) | U32 | Samma adress som redan wired in (se ovan) — nu officiellt dokumenterad, inte längre en gissning från en annan produktserie |
| arm_software_version | 4954-4968 | 4953 (15 reg) | UTF-8 | |
| dsp_software_version | 4969-4983 | 4968 (15 reg) | UTF-8 | |
| (reserved) | 4984-4989 | 4983 (6 reg) | U16 | Fortfarande genuint "Reserved" per dokumentet |

`protocol_no`, `arm_software_version`, `dsp_software_version` är nu
wired in i `models.py` och exponerade som diagnostiska sensorer i
HA-integrationen. Inte ännu läst mot riktig hårdvara (bara mot
`MockModbusUnit`) — nästa gång du kör `scripts/query.py` mot din
SG12RT är det värt att bekräfta att `arm_software_version`/
`dsp_software_version` faktiskt matchar de ASCII-taggar som hittades
live tidigare.

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
5. ~~De skrivbara holding-registren
   (`start_stop`/`power_limitation_switch`/`power_limitation_setting`/
   `night_svg_switch`)~~ — klart: egen `Component`
   (`SungrowSGControl`, `register_space = "holding"`) i `models.py`,
   med strikta `isinstance(value, bool)`-validerare på enum-fälten
   (`start_stop`/`power_limitation_switch`/`feed_in_power_limit_switch`/
   `night_svg_switch`) för att undvika att ett "sant"-värde som råkar
   vara den numeriska stopp-koden (t.ex. `0xCE`, som är truthy i Python)
   tolkas som start. Utökat 2026-08-30 med `power_limitation_adjustment`
   (absolut kW) och hela feed-in power limit-familjen (kapitel 3.1, se
   "Kapitel 3"-avsnittet ovan) — reaktiv-effekt-reglering (kapitel 3.2)
   medvetet lämnad utanför. Wired in i HA-integrationen som `switch.py`
   (start_stop primär, resten config-entity-kategori) och `number.py`
   (power_limitation_setting/_adjustment,
   feed_in_power_limit_value/_ratio). **Inga skrivningar har körts mot en
   riktig inverter ännu** — adress/skala/enum-värden är avlästa ur
   dokumentet och läsverifierade live, men själva skrivvägen är bara
   testad mot `MockModbusConnection`.
6. ~~HA-integrationen exponerar bara sex fält~~ — klart: `sensor.py`,
   `switch.py`, `number.py` täcker alla fält i
   `SungrowSGInverter`/`SungrowSGControl`, med config-flow-togglar för
   att välja bort strängar/MPPT/elmätare.

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
- De skrivbara registren är wired in (`SungrowSGControl`) och adress/
  enum/skala är dubbelbekräftade mot både V1.1.37 och V1.1.80, men **ingen
  skrivning har körts mot en riktig inverter ännu** — bara läsning av de
  aktuella värdena. Fel värde på `start_stop`/`power_limitation_*` kan
  koppla bort invertern från nätet eller stoppa produktionen.
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
