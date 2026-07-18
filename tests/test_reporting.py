from blackterm_recon.models import PortResult,ScanResult
from blackterm_recon.reporting import write_html

def test_html_report(tmp_path):
    result=ScanResult(target="localhost",ip="127.0.0.1",hostname="localhost",started_at="a",finished_at="b",duration_seconds=.1,ports=[PortResult(80,"open","http",1.0)])
    output=write_html(result,tmp_path/"report.html")
    assert output.exists() and "BLACKTERM" in output.read_text(encoding="utf-8")
