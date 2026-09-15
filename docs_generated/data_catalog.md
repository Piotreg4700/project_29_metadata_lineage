# Katalog danych - przetwarzanie danych pogodowych

- Identyfikator uruchomienia: `6ab2c280ea8f`
- Wygenerowano: 2026-06-29T07:50:42.098349+00:00
- Zbiory danych: 4 | Uruchomienia: 4 | Krawedzie lineage: 4

## `weather_bronze`  _( warstwa bronze )_

- **Opis:** Surowe pomiary pogodowe pobrane z REST API, jeden wiersz na pomiar, wzbogacone o metadane pobrania. Bez zadnego czyszczenia.
- **Lokalizacja:** `C:\AWS_28\project_29_metadata_lineage\data\bronze\weather_bronze.parquet`
- **Format:** parquet
- **Liczba wierszy:** 400
- **Utworzone przez uruchomienie:** `78ff21e0c3b0`
- **Suma kontrolna (hash):** `1cc32519a68a385a`

| Kolumna | Typ | Dopuszcza puste | Liczba pustych | Pochodzi z | Opis |
|---|---|---|---|---|---|
| `timestamp` | string | False | 0 | weather_api.records | Czas pomiaru zwrocony przez API (ISO-8601, UTC). |
| `station_id` | string | False | 0 | weather_api.records | Identyfikator stacji pogodowej. |
| `temperature` | double | False | 0 | weather_api.records | Temperatura powietrza w stopniach Celsjusza. |
| `humidity` | double | False | 0 | weather_api.records | Wilgotnosc wzgledna w procentach. |
| `pressure` | double | False | 0 | weather_api.records | Cisnienie atmosferyczne w hPa. |
| `wind_speed` | double | False | 0 | weather_api.records | Predkosc wiatru (m/s). |
| `wind_direction` | integer | False | 0 | weather_api.records | Kierunek wiatru w stopniach (0-359). |
| `rain_mm` | double | False | 0 | weather_api.records | Opad deszczu w milimetrach. |
| `cloud_cover` | integer | False | 0 | weather_api.records | Zachmurzenie w procentach. |
| `_ingested_at` | string | False | 0 | weather_api.records | Znacznik czasu pobrania dodany przez warstwe Bronze (metadane lineage). |
| `_source_file` | string | False | 0 | weather_api.records | Sciezka surowego pliku JSON, z ktorego wczytano ten wiersz (metadane lineage). |

## `weather_silver`  _( warstwa silver )_

- **Opis:** Zwalidowane, odduplikowane i przerzutowane pomiary (tylko poprawne wiersze).
- **Lokalizacja:** `C:\AWS_28\project_29_metadata_lineage\data\silver\weather_silver.parquet`
- **Format:** parquet
- **Liczba wierszy:** 400
- **Utworzone przez uruchomienie:** `89962fe93d2f`
- **Suma kontrolna (hash):** `b31c22e701b0a498`

| Kolumna | Typ | Dopuszcza puste | Liczba pustych | Pochodzi z | Opis |
|---|---|---|---|---|---|
| `timestamp` | timestamp | False | 0 | weather_bronze.timestamp | Sparsowany czas pomiaru (ze strefa czasowa, UTC). |
| `station_id` | string | False | 0 | weather_bronze.station_id | Identyfikator stacji pogodowej. |
| `temperature` | double | False | 0 | weather_bronze.temperature | Zwalidowana temperatura powietrza (Celsjusz) w wiarygodnym zakresie. |
| `humidity` | double | False | 0 | weather_bronze.humidity | Zwalidowana wilgotnosc wzgledna (%). |
| `pressure` | double | False | 0 | weather_bronze.pressure | Zwalidowane cisnienie atmosferyczne (hPa). |
| `wind_speed` | double | False | 0 | weather_bronze.wind_speed | Zwalidowana predkosc wiatru (m/s). |
| `wind_direction` | integer | False | 0 | weather_bronze.wind_direction | Zwalidowany kierunek wiatru (stopnie). |
| `rain_mm` | double | False | 0 | weather_bronze.rain_mm | Zwalidowany opad deszczu (mm). |
| `cloud_cover` | integer | False | 0 | weather_bronze.cloud_cover | Zwalidowane zachmurzenie (%). |
| `is_valid` | boolean | False | 0 | weather_bronze.temperature<br>weather_bronze.humidity<br>weather_bronze.pressure<br>weather_bronze.wind_speed<br>weather_bronze.wind_direction<br>weather_bronze.rain_mm<br>weather_bronze.cloud_cover<br>weather_bronze.timestamp | True, jesli wiersz przeszedl wszystkie reguly walidacji. |

## `weather_hourly_gold`  _( warstwa gold )_

- **Opis:** Wyselekcjonowane godzinowe cechy pogodowe per stacja oraz regulowy wskaznik komfortu.
- **Lokalizacja:** `C:\AWS_28\project_29_metadata_lineage\data\gold\weather_hourly_gold.parquet`
- **Format:** parquet
- **Liczba wierszy:** 68
- **Utworzone przez uruchomienie:** `61ae9cfb7c55`
- **Suma kontrolna (hash):** `3c02061262a5f2ba`

| Kolumna | Typ | Dopuszcza puste | Liczba pustych | Pochodzi z | Opis |
|---|---|---|---|---|---|
| `station_id` | string | False | 0 | weather_silver.station_id | Identyfikator stacji pogodowej. |
| `hour` | timestamp | False | 0 | weather_silver.timestamp | Kubelek godzinowy (UTC), po ktorym agregowane sa metryki. |
| `avg_temperature` | double | False | 0 | weather_silver.temperature | Srednia temperatura w danej godzinie. |
| `avg_humidity` | double | False | 0 | weather_silver.humidity | Srednia wilgotnosc wzgledna w danej godzinie. |
| `avg_pressure` | double | False | 0 | weather_silver.pressure | Srednie cisnienie w danej godzinie. |
| `max_wind_speed` | double | False | 0 | weather_silver.wind_speed | Maksymalna predkosc wiatru w danej godzinie. |
| `total_rain_mm` | double | False | 0 | weather_silver.rain_mm | Sumaryczny opad deszczu w danej godzinie. |
| `avg_cloud_cover` | double | False | 0 | weather_silver.cloud_cover | Srednie zachmurzenie w danej godzinie. |
| `n_measurements` | integer | False | 0 | weather_silver.temperature | Liczba poprawnych pomiarow zagregowanych w kubelku. |
| `comfort_index` | double | False | 0 | weather_silver.temperature<br>weather_silver.humidity<br>weather_silver.wind_speed | Prosty regulowy wskaznik komfortu (0-100) z temperatury/wilgotnosci/wiatru. |

## `station_summary`  _( warstwa report )_

- **Opis:** Analityczne podsumowanie per stacja uzywane przez raport/dashboard.
- **Lokalizacja:** `C:\AWS_28\project_29_metadata_lineage\data\reports\station_summary.csv`
- **Format:** csv
- **Liczba wierszy:** 4
- **Utworzone przez uruchomienie:** `9f196fc9d3b9`
- **Suma kontrolna (hash):** `69500f8d99259f99`

| Kolumna | Typ | Dopuszcza puste | Liczba pustych | Pochodzi z | Opis |
|---|---|---|---|---|---|
| `station_id` | string | False | 0 | weather_hourly_gold.station_id | Identyfikator stacji pogodowej. |
| `hours_covered` | integer | False | 0 | weather_hourly_gold.hour | Liczba roznych kubelkow godzinowych dostepnych dla stacji. |
| `avg_temperature` | double | False | 0 | weather_hourly_gold.avg_temperature | Srednia temperatura ze wszystkich kubelkow godzinowych. |
| `avg_comfort_index` | double | False | 0 | weather_hourly_gold.comfort_index | Sredni wskaznik komfortu ze wszystkich kubelkow godzinowych. |
| `total_rain_mm` | double | False | 0 | weather_hourly_gold.total_rain_mm | Sumaryczny opad deszczu ze wszystkich kubelkow godzinowych. |
| `peak_wind_speed` | double | False | 0 | weather_hourly_gold.max_wind_speed | Najwyzsza zaobserwowana godzinowa maksymalna predkosc wiatru. |
| `comfort_label` | string | False | 0 | weather_hourly_gold.comfort_index | Czytelna etykieta komfortu wyliczona z avg_comfort_index. |
