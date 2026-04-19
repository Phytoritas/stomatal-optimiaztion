# Provenance

## Slice
- dataset_family: public_rda
- slice_id: 2018_farm10_season1_ripe_tomato
- year: 2018
- farm: 10
- season: 1
- crop_raw: 완숙토마토
- crop_class_for_dm: fresh_market
- cultivar: 데이로스
- planting_date: 2018-10-26
- plant_density: 4.0

## Source Workbooks
- sale_workbook: 2018_sale.xlsx
- env_workbook: 2018_env.xlsx
- cultinfo_workbook: 2018_cultInfo.xlsx

## Basis
- floor_area_g_m2: 1000.0
- canonical_basis_source: 총면적
- cult_total_area_m2: 1000.0
- cult_planted_area_m2: 900.0
- rationale: Canonical floor_area_g_m2 is mapped to cultInfo total floor area when available.

## Forcing Fixture
- row_count: 5952
- datetime_range: 2018-10-26 00:00:00 -> 2019-06-30 23:00:00
- datetime_field: 측정시간
- T_air_C: 온도_내부
- RH_percent: 상대습도_내부 with missing -> 70 percent constant
- CO2_ppm: 잔존CO2 with missing -> 420 ppm constant
- wind_speed_ms: constant 0.3 m/s for all rows by user instruction; raw 풍속_외부 ignored
- radiation_raw_field: 일사량_외부
- greenhouse_kind: 비닐
- transmission_factor: 0.8
- radiation_policy: use raw external radiation where observed; fill missing external radiation from KMA ASOS hourly solar radiation at nearest mapped station
- kma_time_alignment: env measurement timestamps are floored to the hour before joining to KMA hourly radiation
- kma_station: 전주 (146)
- kma_station_distance_km: 12.36704105552536
- kma_external_formula: external_W_m^-2 = KMA_hourly_일사_MJ_m^-2 * 1e6 / 3600
- internal_radiation_formula: internal_W_m^-2 = external_W_m^-2 * 0.8
- PAR_conversion_formula: PAR_umol = internal_W_m^-2 * 2.02
- PAR_provenance: Raw 일사량_외부 is treated as W m^-2. KMA ASOS hourly 일사 is provided in MJ m^-2 and converted to hourly mean W m^-2 before greenhouse transmission. Solar-to-PPFD factor 2.02 from Thimijan & Heins (1983) and Apogee Instruments technical note (Blonquist Jr. & Bugbee).
- raw_radiation_observed_rows: 0
- kma_radiation_filled_rows: 5952
- missing_before_interpolation: {"T_air_C": 0, "PAR_umol": 0, "CO2_ppm": 0, "RH_percent": 0, "wind_speed_ms": 0}
- missing_after_interpolation: {"T_air_C": 0, "PAR_umol": 0, "CO2_ppm": 0, "RH_percent": 0, "wind_speed_ms": 0}

## Observed Harvest Fixture
- raw_date_field: 출하일자
- raw_mass_field: 총출하량
- assumption: `총출하량` is treated as fresh shipment mass in kg for each sale record.
- transformation: parse sale date -> aggregate fresh shipment mass by date -> cumulative sum over time.
- sale_record_count: 25
- sale_date_range: 2019-01-17 -> 2019-06-30
- dry_matter_fraction_low: 0.05
- dry_matter_fraction_baseline: 0.065
- dry_matter_fraction_high: 0.09
- baseline_formula: cumulative_DW_g_per_m2 = cumsum(sum(총출하량_kg_by_day) * 1000 * 0.065) / 1000.0
- dry_matter_provenance: user-provided tomato fruit dry matter literature synthesis dated 2026-03-21; baseline 0.065 for fresh-market tomato and 0.095 for cherry/high-solids tomato.
- caveat: This is a proxy conversion from fresh shipment mass. It is not a direct measured fruit dry-weight time series, even though the downstream fixture header uses `Measured_Cumulative_Total_Fruit_DW (g/m^2)`.

## Output Files
- forcing_fixture.csv
- observed_harvest_fixture.csv
- observed_harvest_fixture_dm_sensitivity.csv
- observed_harvest_fixture__planted_area_basis.csv
