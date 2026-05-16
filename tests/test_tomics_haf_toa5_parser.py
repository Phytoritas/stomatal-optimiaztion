from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.observers.toa5_parser import read_toa5_dat


def test_toa5_parser_handles_quoted_headers_and_units(tmp_path: Path) -> None:
    path = tmp_path / "sensor.dat"
    path.write_text(
        "\n".join(
            [
                '"TOA5","station","CR1000"',
                '"TIMESTAMP","RECORD","SolarRad_Avg","LeafTemp1_Avg","Fruit1Diameter_Avg"',
                '"TS","RN","W/m2","Deg C","mm"',
                '"","","Avg","Avg","Avg"',
                '"2025-12-14 06:00:00",1,0,22.5,30.0',
                '"2025-12-14 06:10:00",2,15,23.0,30.2',
            ]
        ),
        encoding="utf-8",
    )

    frame = read_toa5_dat(path)

    assert list(frame.columns) == ["TIMESTAMP", "RECORD", "SolarRad_Avg", "LeafTemp1_Avg", "Fruit1Diameter_Avg"]
    assert frame["TIMESTAMP"].notna().all()
    assert frame["SolarRad_Avg"].tolist() == [0, 15]

