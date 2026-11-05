"""Monitor declared sequential observations after explicitly converting seconds to minutes."""

import polars as pl

from lss4py import control_chart


def main() -> None:
    """Retain pair identity and investigate a signal against frozen Phase I limits."""
    baseline = control_chart(
        pl.DataFrame(
            {
                "sample": ["a", "b", "c", "d", "e", "f"],
                "duration_minutes": [10.0, 11.0, 9.0, 10.0, 14.0, 13.0],
            }
        ),
        column="duration_minutes",
        key_column="sample",
        unit="minutes",
    )
    # This small synthetic baseline demonstrates mechanics, not an established
    # stable process or a recommended Phase I sample size.
    assert baseline.moving_ranges.tolist() == [1.0, 2.0, 1.0, 4.0, 1.0]
    assert baseline.center_line == 1.8
    assert round(baseline.ucl, 4) == 5.8798
    recorded = pl.DataFrame(
        {"sample": ["g", "h", "i"], "duration_seconds": [780.0, 1380.0, 1320.0]}
    )
    converted = recorded.with_columns((pl.col("duration_seconds") / 60).alias("duration_minutes"))
    monitored = control_chart(
        converted,
        column="duration_minutes",
        key_column="sample",
        baseline=baseline,
    )
    assert monitored.unit == "minutes"
    assert monitored.ucl == baseline.ucl
    assert monitored.moving_ranges.tolist() == [10.0, 1.0]
    assert monitored.signal_indices.tolist() == [0]
    assert monitored.signal_source_positions.tolist() == [1]
    signals = monitored.to_frame().filter(pl.col("signal"))
    assert signals["start_key"].to_list() == ["g"]
    assert signals["end_key"].to_list() == ["h"]
    assert recorded["duration_seconds"].to_list() == [780.0, 1380.0, 1320.0]
    print(f"Frozen UCL: {monitored.ucl:.4f} minutes")
    print(signals)
    print("Investigate the g → h change; the signal does not establish its cause.")


if __name__ == "__main__":
    main()
