# Przyklady analizy wplywu

Analiza wplywu odpowiada na pytanie: *jesli ten zbior/kolumna zmieni sie lub przestanie dzialac, ktore wyniki ponizej zostana dotkniete?* Jest wyliczana automatycznie z zarejestrowanego grafu lineage.

## Wplyw na poziomie zbiorow danych

- Zmiana **`weather_bronze`** wplywa na: `weather_silver`, `weather_hourly_gold`, `station_summary`
- Zmiana **`weather_silver`** wplywa na: `weather_hourly_gold`, `station_summary`
- Zmiana **`weather_hourly_gold`** wplywa na: `station_summary`

## Wplyw na poziomie kolumn

- Zmiana **`weather_bronze.temperature`** wplywa na kolumny: `weather_silver.temperature`, `weather_silver.is_valid`, `weather_hourly_gold.avg_temperature`, `weather_hourly_gold.n_measurements`, `weather_hourly_gold.comfort_index`, `station_summary.avg_temperature`, `station_summary.avg_comfort_index`, `station_summary.comfort_label`
- Zmiana **`weather_bronze.wind_speed`** wplywa na kolumny: `weather_silver.wind_speed`, `weather_silver.is_valid`, `weather_hourly_gold.max_wind_speed`, `weather_hourly_gold.comfort_index`, `station_summary.peak_wind_speed`, `station_summary.avg_comfort_index`, `station_summary.comfort_label`
- Zmiana **`weather_silver.humidity`** wplywa na kolumny: `weather_hourly_gold.avg_humidity`, `weather_hourly_gold.comfort_index`, `station_summary.avg_comfort_index`, `station_summary.comfort_label`
