"""Customer CSV ingestion through the installed package without source-tree helpers."""

from lss4py import (
    ColumnRule,
    DataContract,
    NumericLogContract,
    load_csv,
    load_numeric_event_log,
)


def test_installed_numeric_log_ingestion(tmp_path):
    """Retain order-level null loads and parallel child identities on a numeric clock."""
    path = tmp_path / "activities.csv"
    path.write_text(
        "order,load,step,pass,q,s,w,e\n001,L1,Wash,1,12.1,13.1,14.1,40.1\n"
        "001,L2,Wash,1,12.1,13.1,14.1,40.1\n001,,Fold,1,40.1,40.1,40.1,50.1\n"
    )
    contract = NumericLogContract(
        case_id_column="order",
        load_id_column="load",
        activity_column="step",
        pass_column="pass",
        time_columns=("q", "s", "w", "e"),
        unit="minutes",
        clock="operating minutes",
        boundary="arrival through readiness",
    )
    log = load_numeric_event_log(path, contract=contract)
    assert log.height == 3
    assert log.frame["order"].to_list() == ["001"] * 3
    assert log.frame["load"].to_list() == ["L1", "L2", None]
    assert log.frame["q"].to_list()[0] == 12.1


def test_installed_declared_csv_loading(tmp_path):
    """Preserve explicit string identities and unknown source fields."""
    path = tmp_path / "orders.csv"
    path.write_text("id,lead,note\n001,12.3,NA\n")
    frame = load_csv(
        path,
        contract=DataContract(
            columns=(
                ColumnRule("id", kind="string"),
                ColumnRule("lead", minimum=0, unit="minutes"),
            ),
            key_columns=("id",),
            duplicates="error",
        ),
    )
    assert frame.row(0) == ("001", 12.3, "NA")
