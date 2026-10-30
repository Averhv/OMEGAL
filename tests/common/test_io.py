from lab_analysis.common.io import read_text, safe_filename, write_run_info


def test_safe_filename_normalises():
    assert safe_filename("SF 1.5mL/30s!") == "SF_1.5mL_30s"


def test_safe_filename_fallback():
    assert safe_filename("...") == "plot"


def test_write_run_info(tmp_path):
    write_run_info({"n": 5}, tmp_path)
    text = (tmp_path / "_run_info.json").read_text(encoding="utf-8")
    assert '"n": 5' in text
    assert '"timestamp"' in text


def test_read_text_handles_bom(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes("\ufeffhello".encode("utf-8"))
    assert read_text(p) == "hello"