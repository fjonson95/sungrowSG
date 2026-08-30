<img src="custom_components/sungrow_sg/brand/icon@2x.png" alt="" width="96" height="96" align="right">

# sungrowSG — Sungrow SG-serien som riktig Home Assistant-integration

Egen Modbus-integration för Sungrow strängväxelriktare (SG-serien, i första hand
SG12RT), byggd enligt den nya arkitekturen som beskrivs i Home Assistants
utvecklarblogg ["Modernizing Modbus"](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/)
(juli 2026).

`custom_components/sungrow_sg/brand/` innehåller integrationens ikon
(`icon.png`/`icon@2x.png`) — sedan HA 2026.3.0 kan anpassade integrationer
skicka med sin egen ikon direkt i repot (ingen PR till
`home-assistant/brands` behövs), se
[Brands Proxy API-annonseringen](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api).
HA plockar upp den automatiskt, ingen extra konfiguration.

Projektet är uppdelat i två delar, enligt mönstret `trovis-modbus` (bibliotek)
+ `trovis557x` (HA-integration):

- **`library/sungrow-modbus/`** — fristående, HA-oberoende Python-paket som
  modellerar Sungrow SG-enheter mot `modbus_connection.model`
  (register, skalning, enheter, coils). Publiceras separat på PyPI när det är
  moget, testas med `modbus_connection`s pytest-plugin (`mock_modbus_unit` -
  ett in-memory testdubbel, inte en riktig socket-server) för att fånga
  fel i register-ihopkopplingen (fel adressrymd, fel adress, fel skala)
  utan att behöva riktig hårdvara. Ersätter inte ett test mot en riktig
  inverter.
- **`custom_components/sungrow_sg/`** — HACS-distribuerad Home Assistant-
  integration som "vendorar" biblioteket, ber kärnintegrationen `modbus` om
  en unit (delad, serialiserad anslutning — ingen egen socket), och
  exponerar entiteter via config flow + device registry.

## Status

Registerkartan för SG12RT (`docs/register_map.md`,
`library/sungrow-modbus/src/sungrow_modbus/registers.py`) är **läst direkt
ur Sungrows officiella protokolldokument** ("Communication Protocol of PV
Grid-Connected String Inverters" V1.1.37 EN) — adress, datatyp, skala och
enhet per fält, inklusive en adress-offset-fälla i dokumentet (tabellens
nummer är 1-baserade, wire-adressen är −1) som är löst och dokumenterad.

`library/sungrow-modbus` är installerat och testat på riktigt i den här
miljön (Python 3.13, `pip install "modbus-connection[tmodbus]"` —
paketet finns på PyPI och kräver bara Python ≥3.12, tvärtemot ett
tidigare antagande här att bara 3.10 fanns tillgängligt). Det avslöjade
en riktig bugg: `Component.register_space` är `"holding"` som default,
men hela Sungrow-registerkartan ligger i input-registerrymden — utan
`register_space = "input"` i `models.py` (nu fixat) hade varje läsning
mot en riktig inverter träffat fel registerfil. `pytest` går grönt mot
paketets in-memory mock, se `library/sungrow-modbus/tests/`.

**Testad live mot en riktig SG12RT** (`scripts/query.py`) — hittade och
löste en till bugg: `uint32()`-fälten (`total_active_power`,
`total_power_yield` m.fl.) behöver `word_order="little"`, inte
bibliotekets default `"big"` (gav annars ~99 MW respektive ~360 GWh på
en 12kW-inverter). Efter fixen: rimliga värden rakt av.

**Alla PDF-verifierade läsregister är nu wired in i `SungrowSGInverter`**
och livetestade: identitet/firmware, alla AC/DC-mätvärden, temperatur,
MPPT 1/2, per-sträng-ström, hela elmätarblocket (export/import/last),
work state, isolationsresistans m.fl. — se `docs/register_map.md` för
fullständig lista och `scripts/query.py` för att köra det själv. De
skrivbara holding-registren (start/stopp, effektbegränsning, Night SVG)
är fortfarande medvetet lämnade utanför — se "Att göra" i
`docs/register_map.md`.

**`custom_components/sungrow_sg/coordinator.py` + `sensor.py` är nu
kopplade mot alla dessa fält** — 42 sensorer (identitet går till
`DeviceInfo.model`/`sw_version`/`serial_number` istället för egna
entiteter). `coordinator.py` bygger en riktig `ModbusConnection` +
`SungrowSGInverter` (inte längre en `self._inverter = None`-stub) och
stänger den vid unload. Varje `SensorEntityDescription` (device_class,
enhet, state_class, `options` för de två ENUM-sensorerna) är validerad
mot en riktig installerad Home Assistant-core (2024.3.3) genom att
faktiskt konstruera varje sensor och läsa `.state` — noll fel, noll
varningar. Detta är **inte** samma sak som ett test mot en körande HA
med den här integrationen laddad (ingen riktig `ConfigEntry`/`hass`
användes) — se "Att göra" nedan.

## Varför en egen integration (i korthet)

Se den fulla diskussionen i projektanteckningarna, men kort: riktig enhet i
enhetsregistret, UI-konfiguration istället för YAML/mallar, delad
Modbus-anslutning utan buskonflikter med t.ex. Modbus Manager, och möjlighet
att bidra tillbaka till communityn om SG12RT-stödet blir bra.

## Nästa steg

1. ~~Läsa igenom Sungrows officiella protokolldokument register-för-register~~
   — klart, se `docs/register_map.md`.
2. ~~Sätta upp Python 3.12+-miljö och installera `modbus-connection`~~ —
   klart (3.13, se `library/sungrow-modbus/pyproject.toml`).
3. ~~Skriva tester i `library/sungrow-modbus/tests/`~~ — klart mot
   in-memory mock.
4. ~~Köra `scripts/query.py` mot en riktig SG12RT~~ — klart, se ovan.
5. ~~Koppla in resten av de PDF-verifierade läsfälten i `models.py`~~ —
   klart och livetestat, se `docs/register_map.md`.
6. ~~Koppla `coordinator.py`/`sensor.py` mot alla fält i `models.py`~~ —
   klart (42 sensorer), se ovan. Statiskt validerat mot en riktig
   Home Assistant-core, men **inte** kört mot en riktig, laddad HA-instans
   än — `config_flow.py`s `_async_try_connect` är fortfarande en no-op
   (kopplar aldrig faktiskt upp mot invertern under själva config flow-
   steget, bara vid första coordinator-refresh efteråt), och ingen har
   provat att lägga till integrationen i en riktig HA och se att
   entiteterna faktiskt dyker upp korrekt.
7. De skrivbara holding-registren (start/stopp, effektbegränsning,
   Night SVG) är avsiktligt inte wired in som skrivbara än — kräver en
   egen `Component` (annan `register_space`) och försiktig
   hårdvarutestning, se "Att göra" punkt 5 i `docs/register_map.md`.
8. ~~`manifest.json` pekade på `sungrow-modbus==0.0.1` som ett PyPI-krav
   för ett opublicerat paket~~ — löst: `sungrow_modbus` är vendorat rakt
   in i `custom_components/sungrow_sg/sungrow_modbus/` (en committad
   spegel av `library/sungrow-modbus/src/sungrow_modbus/`, se den mappens
   README.md). `manifest.json` kräver nu bara `modbus-connection[tmodbus]`,
   som faktiskt finns på PyPI. Verifierat: hela testsviten i `tests/`
   går grönt även med `sungrow-modbus` avinstallerat helt ur test-venv:et
   — integrationen är självförsörjande, precis som en riktig HA-
   installation (via HACS eller manuell kopiering av
   `custom_components/sungrow_sg/`) skulle vara. Efter ändringar i
   `library/sungrow-modbus/src/sungrow_modbus/`, kör
   `python scripts/sync_vendored_library.py` för att synka den vendorade
   kopian innan commit.
